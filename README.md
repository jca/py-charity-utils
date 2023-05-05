# py-charity-utils

## Usage

The project contains a [devcontainer](https://code.visualstudio.com/docs/devcontainers/containers)
configuration, which allows to run the commands in a reproducible environment

It is advised to run the applications with

- [Visual Studio Code](https://code.visualstudio.com/download) and
  the following extensions installed:
  - `ms-vscode-remote.remote-containers`,
  - `ms-vscode-remote.remote-ssh`
- [Docker](https://docs.docker.com/get-docker/): A container environment
  which allows to run the project in a controlled "sandbox" on your machine

There is a `.devcontainer/.env-dist` provided which should be renamed
to `.devcontainer/.env` and adjusted

## Input format (CSV)

The scripts in this using as input a CSV file with a convention based layout

| meta   | customer_id     | customer_name  | gocardless_email  | item_lines.1.child_name | item_lines.2.child_name |
| ------ | ----------------| -------------- | ----------------- | ----------------------- | ----------------------- |
| title  | Customer ID     | Customer name  | Gocardless email  | Classes - First child   | Classes - Second child  |
| amount |                 |                |                   | 100.00                  | 90.00                   |
| -      | Rows starting   | with a "-" are | skipped           |                         |                         |
|        | ABC1            | Pierre Curie   | pierre@curie.fr   | Irene                   | Eve                     |
|        | ABC2            | Louis Pasteur  | louis@pasteur.fr  | Jean-Baptiste           | Marie-Louise            |

Note:

- The first column is a row which contains column names for use by the modules
- `customer_id` is required for each customer. This is used in invoice generation
- `gocardless_email` is required for gocardless customer exports to be matched
- `abc.1.cde`: allows to generate for example multiple item lines. Here the first
  row's `item_lines` resolves to the following structure in email templates:

```json
{
  "item_lines": [
    {
      "title": "Classes - First child",
      "child_name": "Irene",
      "amount": 100.00,
    },
    {
      "title": "Classes - Second child (10% discount)",
      "child_name": "Eve",
      "amount": 90.00,
    }
  ]
}
```

## Features

### generate-gocardless-payments-csv

Inputs:

- Invoice CSV according to the [input format](#input-format-csv)
- GoCardless customers CSV (name, email, customer_id, mandate_id)

Process: the application will join and transform both CSV input files into a CSV output

Outputs:

- GoCardless payment CSV: this file can be imported in GoCardless

### send-mail-with-attachment

Required environment variables:

- SMTP_HOST
- SMTP_PORT
- SMTP_USERNAME
- SMTP_PASSWORD

Inputs:

- CSV file
- Template email
- Template attachement
- Fields describing CSV file and send-out options

Process:

- Render an email and add a pdf to the output folder
- Send an email with a formatted attachment to each customer
- Send out a summary email back to "SMTP_USERNAME", including an archive of
  the emails and attachments sent

Outputs: logs and generated pdf files in a temporary directory. This script generates and sends emails
