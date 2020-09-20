FROM python:3.7-stretch

RUN set -x \
	&& apt-get update \
	&& apt-get install --no-install-recommends --no-install-suggests -y libc6 groff less

RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install

ENV INSTALL_PATH /cost_reporter
WORKDIR $INSTALL_PATH

RUN pip install pip
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

RUN pip install -e $INSTALL_PATH
RUN chmod +x ./boot.sh
CMD ["./boot.sh"]
