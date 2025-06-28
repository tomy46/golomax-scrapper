{ pkgs }: {
  deps = [
    pkgs.run
    pkgs.mailutils
    pkgs.imagemagickBig
    pkgs.python310
    pkgs.chromium
    pkgs.chromedriver
  ];
}
