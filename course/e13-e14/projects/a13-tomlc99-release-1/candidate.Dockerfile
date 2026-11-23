FROM m.daocloud.io/docker.io/library/python:3.13-slim@sha256:f82c96458eedc847b233e582eb31336f4954b39cae020b6dcf5b3ed0e5cbcd74
WORKDIR /work
COPY toml.c toml.h toml_extra.h toml_json.c Makefile ./
RUN sed -i -e "s|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g" -e "s|security.debian.org|mirrors.tuna.tsinghua.edu.cn|g" /etc/apt/sources.list.d/debian.sources && apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3 update && apt-get -o Acquire::ForceIPv4=true -o Acquire::Retries=3 install -y --no-install-recommends build-essential git strace && rm -rf /var/lib/apt/lists/*
RUN make toml_json
CMD ["./toml_json"]
