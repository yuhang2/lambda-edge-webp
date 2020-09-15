```bash
$ docker build --tag amazonlinux:python37 .
$ docker run --rm --volume $(pwd):/root amazonlinux:python37
$ cd package && zip -r9 ../function.zip .
$ cd .. && zip -g function.zip lambda_function.py
$ cd .. && zip -g function.zip cwebp
```
