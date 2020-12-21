#!/usr/bin/env python
from __future__ import print_function
from future.utils import iteritems

import argparse
import getpass
import json
import logging
import os
import requests
import sys
import time
import threading

def get_token(server_uri, user, password, label, lifetime=None):
    request = {
        'username': user,
        'password': password,
        'label': label
    }
    if lifetime is not None:
        request['lifetime'] = int(lifetime)
    r = requests.post(
        server_uri + "/api/auth/access_token",
        headers = {'Content-Type': 'application/json'},
        data = json.dumps(request)
    )
    r.raise_for_status()
    token = r.json()['access_token']
    return token

def debug_request(r):
    if logging.getLogger().isEnabledFor(logging.DEBUG):    
        logging.debug("REQUEST: " + str(r.request.body))
        logging.debug("RESPONSE: " + str(r.text))

def is_file(f):
    return isinstance(f, file) if sys.version_info[0] == 2 else hasattr(f, 'read')

class Session:

    def __init__(self, *args, **kwargs):
        self.name = args[0]
        self.endpoint = args[1]
        token = kwargs.get('token', '')
        if token == '':
            user = kwargs['user']
            password = kwargs['password']
            app = kwargs.get('app', 'python-api')
            token = get_token(self.endpoint, user, password, app)
        self.session = requests.Session()
        self.session.headers.update({'Authorization': 'Bearer ' + token})
        self.job_counter = 0
        self.submitted_jobs = []
        self.deferred_jobs = []
        self.timer = threading.Timer(3, self.__checkJobs)
        self.timer.start()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def getTokenInfo(self):
        r = self.session.get(self.endpoint + '/api/auth/access_token')
        debug_request(r)
        r.raise_for_status()
        return r.json()

    def app(self, app_id):
        return App(self, app_id)

    def getAppDesc(self, app_id):
        r = self.session.get(self.endpoint + '/api/apps/' + app_id)
        debug_request(r)
        r.raise_for_status()
        return r.json()

    def run(self, app_id, inputs, resources=[], job_name=None):
        # create new job
        if job_name is None:
            job_name = self.name + " - Job " + str(self.job_counter)
        job = Job(self, job_name, app_id, inputs, resources)
        self.job_counter += 1

        # check if job inputs are ready
        if job.isReady():
            self.__submitJob(job)
            self.submitted_jobs.append(job)
        else:
            self.deferred_jobs.append(job)
            print("Deferred job")

        return job

    def runAll(self, app_id, tasks, resources=[], job_name_prefix=None):
        jobs = []
        task_num = 0
        for inputs in tasks:
            if job_name_prefix is None:
                jobs.append(self.run(app_id, inputs, resources))
            else:
                jobs.append(self.run(app_id, inputs, resources, job_name_prefix + str(task_num)))
            task_num += 1
        return jobs

    def getJobs(self):
        r = self.session.get(self.endpoint + '/api/jobs')
        debug_request(r)
        r.raise_for_status()
        return [Job.fromjson(self, job_json) for job_json in r.json()]

    def getJobStatus(self, job_id):
        r = self.session.get(self.endpoint + '/api/jobs/' + job_id)
        debug_request(r)
        r.raise_for_status()
        return r.json()

    def getJobState(self, job_id):
        job_status = self.getJobStatus(job_id)
        return job_status['state']

    def getJobLog(self, job_id, path):
        dir = os.path.abspath(os.path.join(path, os.pardir))
        if not os.path.exists(dir):
            os.makedirs(dir)
        r = self.session.get(self.endpoint + '/api/jobs/' + job_id + '/log', stream=True)
        r.raise_for_status()
        with open(path, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=1024):
                fd.write(chunk)

    def cancelJob(self, job_id):    
        r = self.session.post(
            self.endpoint + '/api/jobs/' + job_id + '/cancel'
        )
        debug_request(r)
        r.raise_for_status()
        print("Cancelled job " + job_id)

    def deleteJob(self, job_id):    
        r = self.session.delete(
            self.endpoint + '/api/jobs/' + job_id
        )
        debug_request(r)
        r.raise_for_status()
        print("Deleted job " + job_id)

    def deleteJobs(self, name):
        r = self.session.delete(
            self.endpoint + '/api/jobs?name=' + name
        )
        debug_request(r)
        r.raise_for_status()
        print("Deleted jobs by name " + name)

    def __uploadFile(self, file):
        r = self.session.post(
            self.endpoint + '/api/files/temp',
            files={'file': file}
        )
        r.raise_for_status()
        file_uri = r.json()['uri']
        #print(file_uri)
        return file_uri

    def __submitJob(self, job):
        # process inputs
        for param, value in iteritems(job.inputs):
            # upload input files
            if is_file(value):
                file_uri = self.__uploadFile(value)
                job.inputs[param] = file_uri
            # read output values
            if isinstance(value, Output):
                job.inputs[param] = value.value()
            # same for arrays
            if isinstance(value, list):
                new_list = []
                for item in value:
                    if is_file(file):
                        file_uri = self.__uploadFile(item)
                        new_list.append(file_uri)
                    elif isinstance(item, Output):
                        new_list.append(item.value())
                    else:
                        new_list.append(item)
                job.inputs[param] = new_list

        # prepare request
        req = {}
        req['name'] = job.name
        req['inputs'] = job.inputs
        if len(job.resources) > 0:
            req['resources'] = job.resources
        #print(req)

        # submit job
        r = self.session.post(
            self.endpoint + '/api/apps/' + job.app_id, 
            headers = {'Content-Type': 'application/json'},
            data = json.dumps(req)
        )
        debug_request(r)
        if r.status_code == 201:
            resp = r.json()
            job_id = resp['id']
            job.id = job_id
            job_state = resp['state']
            job.state = job_state
            print("Job submitted: " + job_id)
        else:
            #r.raise_for_status()
            job.state = 'FAILED'
            print("Failed to submit job! %d(%s) %s" % (r.status_code, r.reason, r.text))

    def __checkJobs(self):
        try:
            # check state of submitted jobs
            for job in self.submitted_jobs[:]:
                if job.state == 'DONE' or job.state == 'FAILED' or job.state == 'CANCELLED':
                    self.submitted_jobs.remove(job)
                else:
                    job_status = self.getJobStatus(job.id)
                    job_state = job_status['state']
                    if job_state != job.state:
                        print("Job " + job.id + " state: " + job_state)
                        job.state = job_state
                        if job.state == 'DONE' or job.state == 'FAILED':
                            job._result = job_status['result']

            # check readiness of deferred jobs
            for job in self.deferred_jobs[:]:
                if job.isReady():
                    self.deferred_jobs.remove(job)
                    self.__submitJob(job)
                    self.submitted_jobs.append(job)
                else:
                    if job.isBroken():
                        self.deferred_jobs.remove(job)
                        job.state = 'BROKEN'
                        print('Found broken job')
        except Exception as err:
            print("Got error while checking jobs:", err)
        finally:
            self.timer = threading.Timer(5, self.__checkJobs)
            self.timer.start()

    def getFile(self, file_uri, path):
        dir = os.path.abspath(os.path.join(path, os.pardir))
        if not os.path.exists(dir):
            os.makedirs(dir)
        if file_uri.startswith('/api/files/'):
            r = self.session.get(self.endpoint + file_uri, stream=True)
        else:
            r = requests.get(file_uri, stream=True)
        r.raise_for_status()
        with open(path, 'wb') as fd:
            for chunk in r.iter_content(chunk_size=1024):
                fd.write(chunk)

    def readFile(self, file_uri):
        if file_uri.startswith('/api/files/'):
            r = self.session.get(self.endpoint + file_uri, stream=True)
        else:
            r = requests.get(file_uri, stream=True)
        r.raise_for_status()
        return r.text

    def close(self):
        self.timer.cancel()

class App:

    def __init__(self, app_id, session):
        self.session = session
        self.id = app_id

    def run(self, inputs, resources=[], job_name=None):
        return self.session.run(self.id, inputs, resources, job_name)

    def runAll(self, tasks, resources=[], job_name_prefix=None):
        return self.session.runAll(self.id, tasks, resources, job_name_prefix)

class Job:

    def __init__(self, session, name, app_id, inputs, resources, id=None, state=None, result=None):
        self.session = session
        self.name = name
        self.app_id = app_id
        self.inputs = inputs
        self.resources = resources
        self.id = id
        self.state = state
        self._result = result

    @classmethod
    def fromjson(cls, session, job_json):
        result = None
        if 'result' in job_json:
            result = job_json['result']
        if job_json['appAlias']:
            app_id = job_json['appAlias']
        else:
            app_id = job_json['appId']
        return cls(session, job_json['name'], app_id, job_json['inputs'],
                   None, job_json['id'], job_json['state'], result)

    def isReady(self):
        is_ready = True
        for param, value in iteritems(self.inputs):
            if isinstance(value, Output):
                if not value.isReady():
                    is_ready = False
                    break
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, Output):
                        if not item.isReady():
                            is_ready = False
                            break
        return is_ready

    def isBroken(self):
        is_broken = False
        for param, value in iteritems(self.inputs):
            if isinstance(value, Output):
                if value.isBroken():
                    is_broken = True
                    break
        return is_broken

    def result(self):
        while True:
            if self.state == 'DONE':
                return self._result
            if self.state == 'FAILED':
                raise JobException("Job is failed!")
            if self.state == 'CANCELLED':
                raise JobException("Job is cancelled!")
            if self.state == 'BROKEN':
                raise JobException("Job is broken!")
            time.sleep(3)

    def output(self, param):
        return Output(self, param)

    def getLog(self, path):
        self.session.getJobLog(self.id, path)

    def getOutput(self, output):
        return self._result[output]

    def getResult(self):
        return self._result

    def cancel(self):
        self.session.cancelJob(self.id)

    def delete(self):
        self.session.deleteJob(self.id)

    def __str__(self):
        return "Job %s %s" % (self.id, self.state)

class JobException(Exception):

    def __init__(self, msg):
        super(JobException, self).__init__(msg)

class Output:

    def __init__(self, job, param):
        self.job = job
        self.param = param

    def isReady(self):
        if self.job.state == 'DONE' and self.job._result != None:
            return True
        else:
            return False

    def isBroken(self):
        if self.job.state == 'FAILED' or self.job.state == 'CANCELLED' or self.job.state == 'BROKEN':
            return True
        else:
            return False

    def value(self):
        if self.isReady():
            return self.job._result[self.param]
        else:
            return None

class CLI(object):

    def __init__(self):
        parser = argparse.ArgumentParser(
            description='Everest CLI',
            usage='''everest.py <command> [<args>]

The commands are:
     get-token  Obtain new client token
''')
        parser.add_argument('command', help='Subcommand to run')
        args = parser.parse_args(sys.argv[1:2])
        command = args.command.replace('-', '_')
        if not hasattr(self, command):
            print('Unrecognized command')
            parser.print_help()
            exit(1)
        getattr(self, command)()

    def get_token(self):
        parser = argparse.ArgumentParser(description='Obtain new client token')
        parser.add_argument('-u', '--user', required=True)
        parser.add_argument('-l', '--label', required=True, help='token label')
        parser.add_argument('-t', '--lifetime', required=False, help='token lifetime is seconds (default is one week)')
        parser.add_argument('-server_uri', required=False, 
            default='https://everest.distcomp.org', 
            help='location of Everest, i.e., http(s)://host:port')
        args = parser.parse_args(sys.argv[2:])
        pswd = getpass.getpass('Password: ')
        token = get_token(args.server_uri, args.user, pswd, args.label, args.lifetime)
        print(token)

if __name__ == "__main__":
    CLI()