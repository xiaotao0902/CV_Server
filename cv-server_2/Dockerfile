FROM ubuntu:14.04

RUN sudo apt-get update
RUN sudo apt-get install -y python-dev
RUN sudo apt-get install --reinstall -y build-essential python-pip python-opencv
RUN sudo pip install numpy
COPY ./ app/

WORKDIR "app/"
RUN sudo rm -rf ./build
RUN make
RUN python setup.py build
RUN sudo python setup.py install
