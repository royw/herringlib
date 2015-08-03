# coding=utf-8
"""
Docker tasks
"""
import os
from herring.herring_app import namespace, task
from herringlib.cd import cd
from herringlib.local_shell import LocalShell
from herringlib.project_settings import Project
from herringlib.simple_logger import info
from herringlib.split_all import split_all

DOCKERFILE = 'Dockerfile'

with namespace('docker'):
    @task(help="command line arguments are directory base names that contain Dockerfiles.  "
               "No args means find and build all containers.")
    def buildcontainers():
        """
        Build docker containers.
        By default find and build all containers.
        If args are present, build just the containers given as command line arguments."""
        for root, dirs, files in os.walk(os.path.join(Project.docker_dir, Project.docker_containers_dir)):
            # info("root: {root}".format(root=root))
            # info("files: {files}".format(files=repr(files)))
            if DOCKERFILE in files:
                # info("Found Dockerfile in {root}".format(root=root))
                repo_dir = split_all(root)[-1]
                if not task.argv or repo_dir in task.argv:
                    tag = "{project}/{dir}".format(project=Project.docker_project, dir=repo_dir)
                    with cd(root):
                        with LocalShell() as local:
                            local.run("docker build -t {tag} .".format(tag=tag).split(' '), verbose=True)
                            info("built container: {root}".format(root=root))
                else:
                    info("skipping {dir}".format(dir=repo_dir))
