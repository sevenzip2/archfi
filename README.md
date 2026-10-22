# archfi

Just a simple bash script wizard to install Arch Linux after you have booted on the official Arch Linux install media.

This is a maintained fork of [MatMoul/archfi](https://github.com/MatMoul/archfi), updated for current Arch Linux.

With this script, you can install Arch Linux with two simple terminal commands.

This wizard is made to install minimum packages (Base, bootloader and optionally archdi).

At the end of this wizard, you can install or launch [archdi](https://github.com/sevenzip2/archdi) (Arch Linux Desktop Install) to install and configure desktop packages.

You can watch the original author's videos to see how to use it [here](https://www.youtube.com/playlist?list=PLytHgIKLV1caHlCrcTSkm5OF2WSVI1_Sq).

## What's new in this fork

- Btrfs flat subvolume layout (`@`, `@home`, `@snapshots`, `@var_log`, `@swap`) with optional compression (none, zstd:1, zstd, lzo)
- Swap partition is optional in auto partitioning, plus zram (zram-generator) and swap file options
- LUKS root works with the systemd based initramfs (`sd-encrypt`), with optional TPM2 / FIDO2 unlock (systemd-cryptenroll)
- systemd-boot with per kernel entries, optional Unified Kernel Images and Secure Boot (sbctl)
- CPU microcode, 32-bit UEFI detection, GPT partition types for root auto-discovery
- English only: the downloadable language files were removed

## How to use

First, boot with the [latest Arch Linux image](https://archlinux.org/download/) with a [bootable device](https://wiki.archlinux.org/title/USB_flash_installation_medium).

Then make sure you have Internet connection on the Arch iso. If you have a wireless connection the [`iwctl`](https://wiki.archlinux.org/title/Iwd#iwctl) command might be useful to you. You can also read the [Network configuration](https://wiki.archlinux.org/title/Network_configuration) from the Arch Linux guide for more detailed instructions.

Then download the script with from the command line:

    curl -fsSLO https://raw.githubusercontent.com/sevenzip2/archfi/master/archfi

Finally, launch the script:

    sh archfi

Then follow the on-screen instructions to completion.

If you require extra help, visit the provided video playlist and follow my example.

## More custom install

    sh archfi -cpl {URL of your custom package list}

You can find a sample custom package list file in the samples folder.

## For developers

You can test your script with this command :

    sh archfi -t {githubusername} {branchname}

Example :

    sh archfi -t sevenzip2 master
