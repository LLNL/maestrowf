FROM ubuntu
LABEL maintainer="Francesco Di Natale dinatale3@llnl.gov"

RUN apt-get update
RUN apt-get install -y python python-pip git
ADD . /maestrowf
RUN pip install -U /maestrowf
