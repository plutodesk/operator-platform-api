FROM us.gcr.io/warehouse-323808/seal:latest

RUN apt-get update && apt-get install -y vim

ADD ./requirements.txt  /code/requirements.txt

RUN pip install -r /code/requirements.txt

ADD ./ /code

WORKDIR /code

CMD ./entrypoint $serve
