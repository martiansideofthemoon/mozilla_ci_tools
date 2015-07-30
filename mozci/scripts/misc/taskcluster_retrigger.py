'''
taskcluster_retrigger.py allows you to retrigger a task from TaskCluster
past its deadline.

The API used is:
    * createTask [1]

[1] http://docs.taskcluster.net/queue/api-docs/#createTask
'''
import datetime
import json
import logging
import sys

from argparse import ArgumentParser

import taskcluster

logging.basicConfig(format='%(asctime)s %(levelname)s:\t %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S')
LOG = logging.getLogger()
LOG.setLevel(logging.DEBUG)


# http://stackoverflow.com/questions/956867/how-to-get-string-objects-instead-of-unicode-ones-from-json-in-python
def byteify(input):
    if isinstance(input, dict):
        return {byteify(key):byteify(value) for key,value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input


def main():
    parser = ArgumentParser()
    parser.add_argument('-r',
                        action="store_true",
                        dest="retrigger",
                        help="It retriggers a TaskCluster task.")

    parser.add_argument("--debug",
                        action="store_true",
                        dest="debug",
                        help="set debug for logging.")

    parser.add_argument('task_ids',
                        metavar='task_id',
                        type=str,
                        nargs='+',
                        help='Task IDs to work with.')

    options = parser.parse_args()

    if options.debug:
        LOG.setLevel(logging.DEBUG)
        LOG.info("Setting DEBUG level")
    else:
        LOG.setLevel(logging.INFO)

    # requests is too noisy and adds no value
    logging.getLogger("requests").setLevel(logging.WARNING)

    queue = taskcluster.Queue()
    if options.retrigger:
        # Since we can't rerun a task past its deadline, we create
        # a new task with a new taskGroupId, expiration, creation and
        # deadline values
        try:
            for t_id in options.task_ids:
                task = queue.task(t_id)
                LOG.debug("Original task:")
                LOG.debug(json.dumps(task))
                new_task_id = taskcluster.slugId()

                artifacts = task['payload'].get('artifacts', {})
                for artifact, definition in artifacts.iteritems():
                    definition['expires'] = taskcluster.fromNow('365 days')

                # The task group will be identified by the ID of the only
                # task in the group
                task['taskGroupId'] = new_task_id
                task['expires'] = taskcluster.fromNow('48 hours')
                task['created'] = taskcluster.stringDate(datetime.datetime.utcnow())
                task['deadline'] = taskcluster.fromNow('24 hours')

                # We need a json object rather than a Python dictionary
                # to submit a task.
                task = json.dumps(task)
                LOG.info("Submitting new task with task_id: {}".format(new_task_id))
                LOG.debug("Contents of new task:")
                LOG.debug(task)
                result = queue.createTask(new_task_id, task)
                LOG.debug(result)
                LOG.info("https://tools.taskcluster.net/task-inspector/#{}/".format(new_task_id))

        except taskcluster.exceptions.TaskclusterAuthFailure as e:
            LOG.debug(str(e))
            # Hack until we fix it in the issue
            if str(e) == "Authorization Failed":
                raise e
                LOG.info("Your credentials do not allow you to make this API call.")
                LOG.info("Your permanent credentials need queue:rerun-task and "
                         "assume:scheduler-id:task-graph-scheduler/* as scopes to work")
                LOG.info("This is defined under 'scopes' in "
                         "http://docs.taskcluster.net/queue/api-docs/#rerunTask")
            elif str(e) == "Authentication Error":
                LOG.info("Make sure that you create permanent credentials and you "
                         "set these environment variables: TASKCLUSTER_CLIENT_ID, "
                         "TASKCLUSTER_ACCESS_TOKEN")
            sys.exit(1)

if __name__ == "__main__":
    main()
