# Ultimatum Game

Mastering the ultimatum game. ^_^



## Quickstart

First of all, you need [docker](https://docs.docker.com/install/) and [docker-compose](https://docs.docker.com/compose/install/)

### Build the project:
```bash
./build.sh
```

### Launch tests:
```bash
docker-compose run test
```

### Launch the survey website locally
```bash
# The default port is 5000
docker-compose up web_socket
```

### Launch the survey website
```bash
# A file socket named ultimatum.sock is created, which can be connected to a nginx/apache
docker-compose up web
```

### Launch jupyter notebook
```bash
# The local address of the website will be printed in the terminal.
docker-compose up notebook
```

### Survey/HITs commands
The following commands require credentials for a AWS user with MTurk policies to be configured in ~/.aws. The folder ~/.aws is mounted onto the container.
```bash
docker-compose run web create_hit                       # create a new mturk HIT
docker-compose run web add_assignments                  # add new assignments to a given task
docker-compose run web approve_and_reject_assignments   # approve/reject assignments and and pay assignments bonus
docker-compose run web pay_bonus_assignments            # pay assignments bonus
docker-compose run web flask routes                     # show the routes for the app.
```

### Web entry points:
- /start/`treatmentid`/ e.g. /start/t00/
- /survey/`treatmentid`/ e.g. /survey/t00/
