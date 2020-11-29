FROM fluxrm/flux-core:centos7-v0.17.0
#FROM fluxrm/flux-sched:centos7-v0.9.0
ENV PATH="/home/fluxuser/.local/bin:$PATH"

RUN curl -sL https://download.open-mpi.org/release/open-mpi/v4.0/openmpi-4.0.5.tar.gz | tar xz && \
    cd ./openmpi-4.0.5 && \
    ./configure && \
    make && \
    sudo make install

COPY . /home/fluxuser/maestrowf
WORKDIR /home/fluxuser/maestrowf
RUN echo `which python3` && python3 --version
RUN echo `which pip3` && pip3 --version
RUN pip3 install -U --user pip
RUN echo "$PWD" && ls -la && pip3 install --user .
RUN pip3 install -U ipython
WORKDIR /home/fluxuser

LABEL maintainer="Francesco Di Natale dinatale3@llnl.gov"
