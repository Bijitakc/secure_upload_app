#!/usr/bin/env bash
set -eu

set -a
source .env.localstack
set +a

terraform "$@"