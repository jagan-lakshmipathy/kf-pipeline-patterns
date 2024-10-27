# We need to use the nvcr.io/nvidia/pytorch image as a base image to support both linux/amd64 and linux_arm64 platforms.
# PyTorch=2.2.0, cuda=12.3.2
# Ref: https://docs.nvidia.com/deeplearning/frameworks/pytorch-release-notes/rel-24-01.html#rel-24-01
FROM nvcr.io/nvidia/pytorch:24.07-py3

RUN pip install kfp
RUN pip install kfp-kubernetes
RUN mkdir -p /opt/kfp_pipeline/

WORKDIR /opt/kfp_pipeline/src
ADD mnist.py /opt/kfp_pipeline/src/mnist.py


RUN chgrp -R 0 /opt/kfp_pipeline \
    && chmod -R g+rwX /opt/kfp_pipeline 

ENTRYPOINT ["python", /opt/kfp_pipeline/src/mnist.py"]
