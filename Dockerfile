FROM ubuntu
LABEL maintainer="Francesco Di Natale dinatale3@llnl.gov"

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    git
ADD . /maestrowf
RUN python3 -m pip install -U /maestrowf
