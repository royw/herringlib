# coding=utf-8
"""
Docker tasks
"""
import os
import shutil

from herring.herring_app import namespace, task
from herringlib.cd import cd
from herringlib.local_shell import LocalShell
from herringlib.mkdir_p import mkdir_p
from herringlib.project_settings import Project
from herringlib.prompt import prompt
from herringlib.simple_logger import info
from herringlib.split_all import split_all
from herringlib.touch import touch

DOCKERFILE = 'Dockerfile'

DOCKERFILE_TEMPLATE = os.path.join(os.path.dirname(__file__), 'dockerfile.template')

with namespace('docker'):
    @task(arg_prompt="Enter the image's name:")
    def new_image():
        """Create a new image directory and populate with a default Dockerfile."""
        names = list(task.argv)
        if not names:
            if Project.prompt and task.arg_prompt is not None:
                name = prompt(task.arg_prompt)
                if name is not None and name.strip():
                    names.append(name)

        for name in names:
            container_dir = os.path.join(Project.docker_dir, Project.docker_containers_dir, name)
            mkdir_p(container_dir)
            # populate container dir with Dockerfile and .dockerignore
            dockerfile = os.path.join(container_dir, 'Dockerfile')
            dockerignore = os.path.join(container_dir, '.dockerignore')
            shutil.copyfile(DOCKERFILE_TEMPLATE, dockerfile)
            touch(dockerignore)
            info("Created folder for new image at: {dir}".format(dir=container_dir))


    @task(depends=['build::containers'])
    def build():
        """
        Build docker images.
        """
        pass

    with namespace('build'):
        @task(help="command line arguments are directory base names that contain Dockerfiles.  "
                   "No args means find and build all containers.")
        def containers():
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

