config/template-Makefile:
<<<<<<< HEAD
	curl --create-dirs https://raw.githubusercontent.com/quintenroets/package-dev-tools/refs/heads/main/config/template-Makefile -o config/template-Makefile
=======
	curl -fsSL --retry 3 --speed-limit 1000 --speed-time 10 https://raw.githubusercontent.com/quintenroets/package-dev-tools/refs/heads/main/config/template-Makefile --create-dirs -o config/template-Makefile
>>>>>>> template

include config/template-Makefile
