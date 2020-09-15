FROM amazonlinux:2

RUN yum update -y
RUN yum install python3 zip -y

WORKDIR /root

CMD ["pip3", "install", "-r", "requirements.txt", "--upgrade", "--target", "./package"]
