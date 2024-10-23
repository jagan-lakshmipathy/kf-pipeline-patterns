# Kubeflow Pipeline Patterns
#### Jagan Lakshmipathy
###### 10-19-2024 


## 1. Introduction
In one of our earlier [work](https://github.com/jagan-lakshmipathy/aks-kf-pipeline-example), we demonstrated step-by-step on how to run [Kubeflow Pipeline](https://www.kubeflow.org/docs/components/pipelines/) (KFP). Please note the difference between the Kubeflow Pipeline (KFP) and Kubeflow Platform. Kubeflow Platform is the all encompassing kubeflow ecosystem and KFP is one of several Kubeflow sub-application within Kubeflow Platform. Like most Kubeflow sub-applications, KFP can be run as a standalone or as a part of the ecosystem. From now on for clarity we will refer KFP(standalone) for the standalone KFP and KFP(embeded) for the KFP running with in the Kubeflow Ecosystem. We will refer to pipline running with in the KFP as simply pipeline. Pipelines are made up of components and we refer to them as components. In our earlier work, we ran a simple pipeline in KFP(standalone). Here we will observe and document some KFP patterns and some working examples of these patterns. Some patterns are applicable only for KFP(standalone) and some are applicable only for KFP(embeded) as the security aspects between them are different. We will highlight these differences here and will provide the working examples. As in the earlier work, we will run these examples in Azure Kubernetes Service (AKS). For the sake of breivity we will not repeat all the steps outlined there. Instead we will highlight only the differences. For this reason we strongly recommend the readers to review the earlier work referenced above before proceeding with this repo. Let's get started.

## 2. Patterns
We classify the patterns into two broad categories:
1. Creational Pattern
2. Running Pattern

### 2.1 Creational Patterns
These patterns are used to identified by the type of underlying components that are used to build the pipeline. There are three types of components (1) Python Component, (2) Container Component, and (3) Importer Component. Let us discuss them in detail:

#### 2.1.1 Python Components
KFP Python Components can be further classified into (1) Lightweight Python Component, and (2) Containerized Python Components.

##### 2.1.1.1 Lightweight Python Components
These components are created using a @dsl.component decorator and they must meet two requirements: (a) component inputs and outputs must have valid type annotations, and (2) The components are self contained and may not reference any symbols defined outside of its body. Please refer to this link for more [details](https://www.kubeflow.org/docs/components/pipelines/user-guides/components/lightweight-python-components/). The decorator can take some arguments. Argument, packages_to_install references python libraries that the component depends on. And pip_index_urls argument list the pip_index urls. Similarly, argument base_image refers to the base image.

##### 2.1.1.2 Containerized Python Components
In this pattern, we can build components with symbol references from other python files outside of component functions. In other words, Containerized Components can depend on symbols defined outside of the functions, imports outside of the function, code in an adjacent python modules etc. Please refer to this link for more [details](https://www.kubeflow.org/docs/components/pipelines/user-guides/components/containerized-python-components/). KFP CLI command can be used to build this component.

Python Components are unique because they abstract most aspects of the container definition away from the user, making it convenient to construct components that use pure Python. Under the hood, the KFP SDK sets the image, commands, and args to the values needed to execute the Python component for the user.

#### 2.1.2 Container Components
Container Components, unlike Python Components, enable component authors to set the image, command, and args directly. This makes it possible to author components that execute shell scripts, use other languages and binaries, etc., all from within the KFP Python SDK.

#### 2.1.3 Importer Components
Unlike the above authoring approaches, an importer component is not a general authoring style but a pre-baked component for a specific use case: loading a machine learning artifact from from a URI into the current pipeline. This authoring approach requires a detailed look and we will visit them in our future work. For now we will refer the readers to this [section](https://www.kubeflow.org/docs/components/pipelines/user-guides/components/importer-component/).

### 2.2 Running Patterns
We could trigger the pipeline run from either inside or outside the cluster where the KFP is ruuning. 

##### 2.2.1 Triggering from inside the Cluster
First let's consider triggering the pipeline from inside the cluster. We can trigger the pipeline from inside the cluster by leveraging the kubernetes manifest as shown in [aks-kf-pipeline-example](https://github.com/jagan-lakshmipathy/aks-kf-pipeline-example). This we call as the Manifest Pattern. We have displayed that manifest here for your convenience. In this Job manifest, we create a Pod and run a container image called pipeline-example:latest that is located in the ACR. This image runs a trivial task. We created this image using the Dockerfile provided in the repo above. To run this image, the Kubeflow pipeline requires root authentication. See [here](https://www.kubeflow.org/docs/components/pipelines/concepts/pipeline-root/) to understand the concepts of pipeline root. This manifest below mounts ServiceAccount token volume that is used to authenticate with the Kubeflow Pipelines API. We have defined Job.spec.template.spec.volumes and  Job.spec.template.spec.containers.volumeMounts to project the serviceAccountToken as described [(here)](https://www.deploykf.org/user-guides/access-kubeflow-pipelines-api/).

```
apiVersion: batch/v1
kind: Job
metadata:
  name: pipeline-example
  namespace: kubeflow
spec:
  template:
    metadata:
      labels:
        kubeflow-pipelines-api-token: "true"
    spec:
      containers:
      - name: pytorch-container
        image: <your acr name>.azurecr.io/kubeflow/pipeline-example:latest
        imagePullPolicy: Always
        #command: ["torchrun"]
        #args: 
        resources:
          limits:
            nvidia.com/gpu: 1
        volumeMounts:
          - mountPath: /var/run/secrets/kubeflow/pipelines
            name: volume-kf-pipeline-token
            readOnly: true
      volumes:
        - name: volume-kf-pipeline-token
          projected:
            sources:
              - serviceAccountToken:
                  path: token
                  expirationSeconds: 7200
                  audience: pipelines.kubeflow.org
      tolerations:
      - key: "sku"
        operator: "Equal"
        value: "gpu"
        effect: "NoSchedule"
      restartPolicy: OnFailure
  backoffLimit: 4
  completions: 1
  parallelism: 2
```

The above manifest pattern can be used to run on both KFP(embeded) and KFP(standalone) alike. This manifest will be applied using the kubectl command from your kubernetes console.

The following is the Client Pattern. This pattern leverages the default kfp.Client(). We specify the local UI service when creating the client. This pattern will work only in the KFP(standalone) mode as the KFP backend and UI don't enforce any authentication. 
```
    compiler.Compiler().compile(
        pipeline_func=model_pipeline, package_path=__file__.replace('.py', '.yaml'))

    _kfp_ui_and_port = os.getenv('KFP_UI_HOST_AND_PORT', 'http://ml-pipeline-ui:80')
    kfp_client = kfp.Client(ui_host=_kfp_ui_and_port)


    kfp_client.create_run_from_pipeline_package("./your-pipeline.yaml")
```

##### 2.2.2 Triggering from outside the Cluster
When running the pipeline from outside the cluster, again two approaches are possible one each for the KFP(embeded) and KFP(standalone). Both approaches are a variant of the Client Pattern described above. The following example shows how to trigger the pipeline from outside in the KFP(standalone) mode. In this mode, the approach is similar to the Client Pattern snippet shown in section 2.2.1 with the exception that host url has to be provided as you are running this code from outside the cluster. The following pattern is what we call as the Default Client Pattern. we also need do the port forwarding of Kubeflow Pipeline UI using the kubectl as follows as we will use the localhost to forward the requests. Please note the host name "host.docker.internal" in the snippet below. This is how we refer to the localhost from within the docker container in MacOs. We ran the following code from with in a docker container in our MacOS host. We used the Dockerfile.pipeline to create the docker image and deployed it in our local docker.
```
# change `--namespace` if you deployed Kubeflow Pipelines into a different namespace
kubectl port-forward --namespace kubeflow svc/ml-pipeline-ui 3000:80
```
then create a kfp.Client() against the forwarded port of the Kubflow Pipeline Service. This example is provided in thi repo under the file mnist-pipeline2.yaml. We have provided a step-by-step approach to run this example in section 3 below. 
```
    compiler.Compiler().compile(
        pipeline_func=model_pipeline, package_path=__file__.replace('.py', '.yaml'))

    _kfp_host_and_port = os.getenv('KFP_API_HOST_AND_PORT', 'http://host.docker.internal:8888')
    _kfp_ui_and_port = os.getenv('KFP_UI_HOST_AND_PORT', 'http://host.docker.internal:8080')
    kfp_client = kfp.Client(host=_kfp_host_and_port, ui_host=_kfp_ui_and_port)


    kfp_client.create_run_from_pipeline_package("./mnist-pipeline2.yaml")
```
As mentioned before, the above Default Client Pattern will not work in our KFP(embedded) case. We need to create an authenticated kfp.Client() as described [here](https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/connect-api/). We refer to this as Authenticated Client Pattern. We didn't provide a working example for this as it requires a Kubefow Platform to run this

## 3. Running the Default Client Pattern from outside the cluster
In this section we will outline the steps to run the Default Client Pattern. Code for this pattern is provided in this repo. We have 4 files besides the README. Two docker files (a) Dockerfile, and (b) Dockerfile.pipeline. Two python files mnist.py and mnist\_pipeline2.py. The first python file is the actual training workload that we run inside KFP. The mnist\_pipeline2.py is actually the trigger script that we run from our localhost from within a docker container. We assume Docker is installed in your localhost. We are run this demo on our MacOS. Let's begin.

As mentioned before, we will follow the steps outlined in our earlier [work](https://github.com/jagan-lakshmipathy/aks-kf-pipeline-example)work. Follow steps 4 through 12 outlined there with minor changes. You will use the Dockerfile and provided here as opposed to Dockerfile in that repo. Similarly, you workload file will be mnist.py as opposed to the component_with_optional_inputs.py. 

Now, you will create 