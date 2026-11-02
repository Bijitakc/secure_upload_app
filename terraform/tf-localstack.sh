#!/usr/bin/env bash
set -eu

set -a
source .env.terraform
set +a

terraform "$@"