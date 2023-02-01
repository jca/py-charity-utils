#!/usr/bin/env bash
set -euf -o pipefail
script_dir="${BASH_SOURCE[0]%/*}"
build_dir="${script_dir}/../../build"
src_dir="${script_dir}/../../src"

poetry install --directory="${src_dir}"

mkdir -p "${build_dir}"
output_dir="$(mktemp --directory --tmpdir="${build_dir}" -t tmp.XXXXXXXXXX.test-results)"
template_dir="${script_dir}"

poetry run --directory "${src_dir}" -- \
    send-mail-with-attachment \
        --id-field invoice_id \
        --email-field parent_email \
        --input-request-csv "${template_dir}/invoice-requests.csv" \
        --input-email-template-html "${template_dir}/email.html" \
        --input-attachment-template-html "${template_dir}/invoice.html" \
        --attachment-file-prefix "invoice" \
        --email-subject "Your invoice" \
        --output-dir "${output_dir}" \
        # --force
