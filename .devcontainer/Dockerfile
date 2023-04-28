FROM python:3.10

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME

# Install APT dependencies
RUN export DEBIAN_FRONTEND=noninteractive \
    && apt update \
    && apt install -y \
        wkhtmltopdf \
        gem shellcheck \
    && apt -qq autoremove \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
RUN pip3 install \
    poetry \
    pre-commit \
    mypy

# Cache pre-commit hooks globally
COPY .pre-commit-config.yaml .
RUN git init . && pre-commit install-hooks

# Ensure the poetry environment is visible to VSCode
RUN poetry config virtualenvs.in-project true

ENTRYPOINT [ "/bin/bash" ]
