# Kubeflow Pipeline Patterns
#### Jagan Lakshmipathy
###### 10-19-2024 


## 1. Introduction
In one of our earlier [work](https://github.com/jagan-lakshmipathy/aks-kf-pipeline-example), we demonstrated step-by-step on how to run a kubeflow pipeline [Kubeflow KFP](https://www.kubeflow.org/docs/components/pipelines/) (KFP). Please note the difference between the Kubeflow Pipeline (KFP) and Kubeflow Platform. Kubeflow Platform is the all encompassing kubeflow ecosystem and KFP is one of several Kubeflow sub-application within Kubeflow Platform. Like most Kubeflow sub-applications, KFP can be run as a standalone. In our earlier work, we ran the KFP as a standalone application. Here we will observe and document some KFP patterns and some working examples of these patterns. Some patterns are applicable only KFP and some are applicable only for Kubeflow Platform as the security aspects between KFP and Kubeflow Platform are different.We will highlight these differences here and will provide the working examples for KFP only. As in the earlier work, We will run these examples in Azure Kubernetes Service (AKS). For the sake of breivity we will not repeat all the steps outlined there. Instead we will highlight only the differences. For this reason we strongly recommend the readers to review the earlier work referenced above before proceeding with this repo. Let's get started.

## 2. Patterns
We classify the patterns into two broad categories:
1. Creational Pattern
2. Running Pattern

### 2.1 Creaational Patterns
These patterns are used to create Kubeflow Pipeline. These patterns can be further classified into 3 major categories: (1) Python Component, (2) Container Component, and (3) Importer Component. Let us discuss them in detail:

#### 2.1.1 Python Components
KFP Python Components can be further classified into (1) Lightweight Python Component, and (2) Containerized Python Components.

##### 2.1.1.1 Lightweight Python Components
These components are created using a @dsl.component decorator it must meet two requirements: (a) component inputs and outputs must have valid type annotations, and (2) The components are complete and may not reference any symbols defined outside of its body. Please refer to this link for more [details](https://www.kubeflow.org/docs/components/pipelines/user-guides/components/lightweight-python-components/). The decorator can take some arguments. Argument, packages_to_install references python libraries that the component depends on. And pip_index_urls argument list the pip_index urls. Similarly, argument base_image refers to the base image.

##### 2.1.1.2 Containerized Python Components
In this pattern, we can build components with symbol references from other python files outside of component functions. In other words, Containerized Components can depend on symbols defined outside of the functions, imports outside of the function, code in a adjacent python modules etc. Please refer to this link for more [details](https://www.kubeflow.org/docs/components/pipelines/user-guides/components/containerized-python-components/). KFP CLI command can be used to build this component.

Python Components are unique because they abstract most aspects of the container definition away from the user, making it convenient to construct components that use pure Python. Under the hood, the KFP SDK sets the image, commands, and args to the values needed to execute the Python component for the user.

#### 2.1.2 Container Components
Container Components, unlike Python Components, enable component authors to set the image, command, and args directly. This makes it possible to author components that execute shell scripts, use other languages and binaries, etc., all from within the KFP Python SDK.

#### 2.1.3 Importer Components
What is a Importer Component?

### 2.2 Running Patterns
We could run pipelines either from inside or from outside the cluster where the Kubeflow Platform or Kubeflow Pipeline (KFP) is ruuning. 

##### 2.2.1 Running from inside the Cluster
First let's consider running the pipeline from inside the cluster. When running the pipeline from inside the cluster using the Kubeflow Platform or KFP we can leverage the kubernetes manifest as shown in [aks-kf-pipeline-example](https://github.com/jagan-lakshmipathy/aks-kf-pipeline-example). The working example provided in ask-kf-pipeline-example referenced here will serve as an example for the manifest pattern. We displayed that manifest here for your convenience.In this Job manifest, we create a Pod and run a container image called pipeline-example:latest that is located in the ACR. This image runs a trivial task. We created this image using the Dockerfile provided in the repo above. To run this image, the Kubeflow pipeline requires root authentication. See [here](https://www.kubeflow.org/docs/components/pipelines/concepts/pipeline-root/) to understand the concepts of pipeline root. This manifest below mounts ServiceAccount token volume that is used to authenticate with the Kubeflow Pipelines API. We have defined Job.spec.template.spec.volumes and  Job.spec.template.spec.containers.volumeMounts to project the serviceAccountToken as described [(here)](https://www.deploykf.org/user-guides/access-kubeflow-pipelines-api/).

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

This above manifest pattern can be used to run on both Kubernetes Platform or KFP. If you are running a KFP we can run the pipeline using the kfp.Client() as follows as the KFP backend and UI don't enforce any authentication. 
```
    compiler.Compiler().compile(
        pipeline_func=model_pipeline, package_path=__file__.replace('.py', '.yaml'))

    _kfp_ui_and_port = os.getenv('KFP_UI_HOST_AND_PORT', 'http://ml-pipeline-ui:80')
    kfp_client = kfp.Client(ui_host=_kfp_ui_and_port)


    kfp_client.create_run_from_pipeline_package("./your-pipeline.yaml")
```
The code utilizes the defalt kfp.Client() that references the Kubeflow Pipeline UI running within the cluster. This pattern we call as the Client Pattern.

##### 2.2.2 Running from outside the Cluster
When running the pipeline from outside the cluster, again two approaches are possible one each for the Kubeflow platform and KFP. For KFP, we can leverage the following Client Pattern.T his approach is very similar to the Client Pattern discused in 2.2.1 with the exception that host url has to be provided as you are running this code from outside the cluster. we do the port forwarding of Kubeflow Pipeline UI using the kubeclt as follows:
```
# change `--namespace` if you deployed Kubeflow Pipelines into a different namespace
kubectl port-forward --namespace kubeflow svc/ml-pipeline-ui 3000:80
```
then create a kfp.Client() against the forwarded port of the Kubflow Pipeline Service. This example is provided in thi repo under the file mnist-pipeline2.yaml. We have provided a step-by-step approach to run this example in section 3 beelow. 
```
    compiler.Compiler().compile(
        pipeline_func=model_pipeline, package_path=__file__.replace('.py', '.yaml'))

    _kfp_host_and_port = os.getenv('KFP_API_HOST_AND_PORT', 'http://host.docker.internal:8888')
    _kfp_ui_and_port = os.getenv('KFP_UI_HOST_AND_PORT', 'http://host.docker.internal:8080')
    kfp_client = kfp.Client(host=_kfp_host_and_port, ui_host=_kfp_ui_and_port)


    kfp_client.create_run_from_pipeline_package("./mnist-pipeline2.yaml")
```
For the Kubeflow Platform case, the code involves creating an authenticated kfp.Client() as described [here](https://www.kubeflow.org/docs/components/pipelines/user-guides/core-functions/connect-api/). We refer to this as Authenticated Client Pattern. We didn't provide a working example for this as it requires a Kubefow Platform to run this

## Running the Client Pattern from outside the cluster
We classify the patterns into two broad categories: