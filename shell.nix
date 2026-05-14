{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = [
    # Docker CLI & BuildKit
    pkgs.docker
    pkgs.docker-compose

    # wrapper so nix’s docker binary points at your host’s socket
    pkgs.makeWrapper

    # Python + all your backend deps
    pkgs.python311
    pkgs.python311Packages.sqlalchemy
    pkgs.python311Packages.alembic
    pkgs.python311Packages.psycopg2
    pkgs.python311Packages.python-dotenv
  ];

  shellHook = ''
    if [ -S /var/run/docker.sock ]; then
      makeWrapper ${pkgs.docker}/bin/docker $out/bin/docker \
        --set DOCKER_HOST unix:///var/run/docker.sock
    fi
  '';
}
