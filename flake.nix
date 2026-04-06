{
  description = "dauber - Canvas LMS CLI";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
      in
      {
        devShells.default = pkgs.mkShell {
          packages = with pkgs; [
            python311
            uv
            ruff
          ];

          shellHook = ''
            export UV_PYTHON=${pkgs.python311}/bin/python3.11
          '';
        };
      });
}
