import os
from typing import Optional

import kfp
from kfp import compiler
from kfp import dsl
from kfp.dsl import component, Output

# In tests, we install a KFP package from the PR under test. Users should not
# normally need to specify `kfp_package_path` in their component definitions.
_KFP_PACKAGE_PATH = os.getenv('KFP_PACKAGE_PATH')


@dsl.container_component
def model_train():
    #return dsl.ContainerSpec(image='registry.digitalocean.com/do-dev-jagan-06022024/kubeflow/pipeline-example:latest', 
    return dsl.ContainerSpec(image='jaganacr10212024.azurecr.io/kubeflow/pipeline-example:latest', 
                             command=['/bin/sh'], args=['-c' ,' python mnist.py --epochs 2 --no-cuda --save-model'])


@dsl.pipeline
def model_pipeline():
    # greeting argument is provided automatically at runtime!
    mt = model_train()
    print('Printing mt: ', mt)


if __name__ == "__main__":
    # execute only if run as a script
    compiler.Compiler().compile(
        pipeline_func=model_pipeline, package_path=__file__.replace('.py', '.yaml'))

    _kfp_host_and_port = os.getenv('KFP_API_HOST_AND_PORT', 'http://host.docker.internal:8888')
    _kfp_ui_and_port = os.getenv('KFP_UI_HOST_AND_PORT', 'http://host.docker.internal:8080')
    kfp_client = kfp.Client(host=_kfp_host_and_port, ui_host=_kfp_ui_and_port)


    kfp_client.create_run_from_pipeline_package("./mnist_pipeline2.yaml")
