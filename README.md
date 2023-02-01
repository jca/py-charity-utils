# py-mail-templates

## Usage

The project contains a [devcontainer](https://code.visualstudio.com/docs/devcontainers/containers) configuration, which allows to run the commands in a controlled environment

It is advised to run the applications with

- [Visual Studio Code](https://code.visualstudio.com/download) and the following extensions installed: `ms-vscode-remote.remote-containers`, `ms-vscode-remote.remote-ssh`
- [Docker](https://docs.docker.com/get-docker/): A container environment which allows to run the project in a controlled "sandbox" on your machine

## Features

### send-mail-with-attachment

- Env:
  - SMTP_HOST
  - SMTP_USERNAME
  - SMTP_PASSWORD
- Inputs:
  - Invoice CSV (name, email, invoice number, payment date, item line, price, payment method)
- Outputs:
  - CSV (...all input fields, email status, email date)

- Application will:
  - Render an email and add a pdf to the output folder
  - Send an email with a formatted attachment to each recipient
  - Send out a summary email back to the original "SMTP_USERNAME", including an archive of the emails and attachment sent

Example usage:

```bash
# From within the container
(cd src && poetry run send-mail-with-attachment --help)
```

### generate-gocardless-payment-csv (TODO)

- Inputs:
  - Invoice CSV (name, email, invoice number, payment date, item line, price, payment method)
  - GoCardless customers CSV (name, email, customer_id, mandate_id)
- Outputs:
  - GoCardless payment CSV

- Application will:
  - Query each payment id and save
    - gocardless payment status
    - gocardless payment date
    - gocardless payment amoun
    - outstanding amount
  - Output a summary detail for all new payments
  - Generate a new CSV file

Example usage:

```bash
(cd src && poetry run generate-gocardless-payment-csv --help)
```
