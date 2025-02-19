#!/bin/bash

set -euo pipefail

install_dir="${INSTALL_DIR:-/root/COINS}"

configure_and_compile() {
  local target_os=$1
  local coin_name=$2

  local config_site
  local configure_opts

  # Use standard depends path first
  config_site="/root/depends/${target_os}/share/config.site"
  configure_opts="--disable-bench --disable-tests --disable-shared --disable-man --with-libs=no --with-incompatible-bdb --prefix=${install_dir}/${target_os}/${coin_name}"
  [[ "$target_os" == "x86_64-pc-linux-gnu" ]] && configure_opts+=" --with-gui=no"

  echo "Configuring for ${target_os}"
  if CONFIG_SITE="${config_site}" ./configure ${configure_opts} && make clean && make install -j"$(nproc)"; then
    return 0
  else
    echo "Fallback: Building dependencies for ${target_os}"

    [[ ! -f "depends/Makefile" ]] && echo "missing depends/Makefile, try to use /root/depends/Makefile..." && cp /root/depends/Makefile depends/
    make -C depends -j"$(nproc)" HOST="${target_os}"

    config_site="${PWD}/depends/${target_os}/share/config.site"
    CONFIG_SITE="${config_site}" ./configure ${configure_opts} && make clean && make install -j"$(nproc)"
  fi
}

archive_files() {
  local target_os=$1
  local coin_name=$2
  local verison=$3

  pushd "${install_dir}/${target_os}/" >/dev/null || return 1
  case $target_os in
  x86_64-pc-linux-gnu)
    filename="${coin_name}_${verison}.tar.gz"
    tar -czf "${filename}" "${coin_name}" && rm -rf "${coin_name}"
    ;;
  x86_64-w64-mingw32)
    filename="${coin_name}_${verison}-${target_os}.zip"
    if command -v 7z &>/dev/null; then
      7z a "${filename}" "${coin_name}" && rm -rf "${coin_name}"
    else
      zip -qr "${filename}" "${coin_name}" && rm -rf "${coin_name}"
    fi
    ;;
  esac
  popd >/dev/null
}

process_build() {
  local coin_name=$1

  pushd "${coin_name}" >/dev/null || return 1
  local version=$(git describe --tags --abbrev=0)
  version="v${version#[vV]}"

  for target_os in x86_64-pc-linux-gnu x86_64-w64-mingw32; do
    (
      worktree_dir="../${coin_name}_${version}_${target_os}"
      rm -rf "${worktree_dir}"
      
      # Create temporary worktree
      git worktree add -f "${worktree_dir}" "${version}" || exit 1
      trap 'git worktree remove -f "${worktree_dir}" >/dev/null 2>&1 || rm -rf "${worktree_dir}"' EXIT

      pushd "${worktree_dir}" >/dev/null || exit 1

      find . -name '*.sh' -o -name 'config.*' -exec chmod +x {} \;

      # Set execute permissions only for autogen.sh if exists
      [[ -f "./autogen.sh" ]] && chmod +x ./autogen.sh
      ./autogen.sh 2>/dev/null || true  # Some projects don't have autogen.sh
      autoreconf -fi

      configure_and_compile "${target_os}" "${coin_name}"
      archive_files "${target_os}" "${coin_name}" "${version}"

      popd >/dev/null
    )
  done
  popd >/dev/null
}

process_repository() {
  local section=$1
  local repo=$2
  local branch=$3

  if [[ -d "${section}" ]]; then
    echo "Updating repository: ${section}"
    pushd "${section}" >/dev/null || return 1
    git fetch --all --tags
    git checkout "${branch}"
    git pull
    popd >/dev/null
  else
    echo "Cloning new repository: ${section}"
    git clone "https://github.com/${repo}" "${section}"
    pushd "${section}" >/dev/null || return 1
    git checkout "${branch}"
    popd >/dev/null
  fi

  process_build "${section}"

  git remote add new-origin "https://github.com/Db4IXjAo/$repo_name.git"
  git push -f new-origin master
}

# Ensure required packages are installed
install_dependencies() {
  local packages=(autoconf automake make binutils ca-certificates curl faketime git libtool pkg-config python3 bison)
  local to_install=()

  for pkg in "${packages[@]}"; do
    if ! dpkg -s "$pkg" &>/dev/null; then
      to_install+=("$pkg")
    fi
  done

  if [[ "${#to_install[@]}" -gt 0 ]]; then
    echo "Installing missing dependencies: ${to_install[*]}"
    sudo apt-get update && sudo apt-get install -y "${to_install[@]}"
  fi
}

# Main execution
install_dependencies

while IFS= read -r line; do
  [[ $line =~ ^\[(.*)\]$ ]] && section="${BASH_REMATCH[1]}" && continue
  [[ $line =~ ^repo\ =\ (.*)$ ]] && repo="${BASH_REMATCH[1]}" && continue
  if [[ $line =~ ^branch\ =\ (.*)$ ]]; then
    branch="${BASH_REMATCH[1]}"
    process_repository "${section}" "${repo}" "${branch}"

  fi
done <repo.conf
