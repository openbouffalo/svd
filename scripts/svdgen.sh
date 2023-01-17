#!/usr/bin/env bash

# Copyright 2023 OpenBouffalo
#
# Licensed under the Apache License, Version 2.0 <LICENSE-APACHE or
# https://www.apache.org/licenses/LICENSE-2.0> or the MIT license <LICENSE-MIT
# or https://opensource.org/licenses/MIT>, at your option. This file may not be
# copied, modified, or distributed except according to those terms.

set -o errexit
set -o nounset
set -o pipefail

# Build directory.
O="${O:-build}"
# The path to the checked out bl_mcu_sdk repository.
MCU_SDK_PATH="${MCU_SDK_PATH:-${O}/bl_mcu_sdk}"
# The style used by clang-format.
CLANG_FORMAT_STYLE="{BasedOnStyle: google, ColumnLimit: 2048}"
# The directory of this script.
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

show_help() {
  cat <<EOF
Usage: $(basename "$0") [soc]
EOF
  exit 1
}

# Checks whether required executables are installed.
check_prerequisites() {
  local bins=("git" "python" "clang-format")

  for bin in "${bins[@]}"; do
    if ! command -v "${bin}" > /dev/null; then
      echo "Missing executable ${bin} in \$PATH! Resolve this to continue."
      return 1
    fi
  done
}

prepare() {
  # Create the build directory.
  if [ ! -d "${O}" ]; then
    mkdir -p "${O}"
  fi

  # Clone the SDK.
  if [ ! -d "${MCU_SDK_PATH}" ]; then
    echo "Cloning bl_mcu_sdk to ${MCU_SDK_PATH}"
    git clone --depth 1 https://github.com/bouffalolab/bl_mcu_sdk "${MCU_SDK_PATH}"
  fi

  # Prepare the output directories for the current SoC.
  if [ ! -d "${O}/${soc}" ]; then
    mkdir "${O}/${soc}"
    mkdir "${O}/${soc}/peripherals"
  fi
}

# Prints a list of peripheral header paths for the given SoC.
list_peripheral_headers() {
  local hw_dir="${MCU_SDK_PATH}/drivers/soc/${soc}/std/include/hardware"

  for header_path in "${hw_dir}/"*_reg.h; do
    echo "${header_path}"
  done
}

# Generates a JSON peripheral manifest by parsing the given C header.
generate_peripheral_manifest() {
  local manifest_path="${1}"
  local header_path="${2}"

  clang-format --style="${CLANG_FORMAT_STYLE}" "${header_path}" \
    | python "${SCRIPT_DIR}/creg2json.py" - > "${manifest_path}"
}

main() {
  local soc="bl808"

  # Check that the necessary prerequisites are available.
  check_prerequisites

  # Check out SDK and create build directories.
  prepare

  # Create a list of peripheral header paths.
  readarray -t peripheral_headers <<< "$(list_peripheral_headers)"

  for peripheral_header in "${peripheral_headers[@]}"; do
    local file_name="$(basename "${peripheral_header}")"
    local file_prefix="$(basename "${peripheral_header}" ".h")"
    local json_manifest="${O}/${soc}/peripherals/${file_prefix}.json"

    echo "Generating JSON manifest for ${file_name} and saving it to ${json_manifest}"
    generate_peripheral_manifest "${json_manifest}" "${peripheral_header}"
  done
}

main "$@"

