FROM ubuntu
LABEL maintainer="Francesco Di Natale dinatale3@llnl.gov"

ADD . /maestrowf
RUN apt-get update && apt-get install -y python python-pip
RUN pip install /maestrowf
