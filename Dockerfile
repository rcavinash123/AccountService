FROM python:2.7
RUN apt update
COPY . /AccountService
WORKDIR /AccountService
ADD requirements.txt /AccountService/requirements.txt
RUN pip install -r /AccountService/requirements.txt
EXPOSE 4004
ENTRYPOINT ["python"]
CMD ["account.py"]