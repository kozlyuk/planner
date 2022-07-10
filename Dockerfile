###########
# BUILDER #
###########

# pull official base image
FROM python:3.8-alpine as builder

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install source packages dependencies
 RUN apk add --update gcc musl-dev mariadb-connector-c-dev

# install dependencies
COPY ./requirements.txt .
RUN pip install --upgrade pip
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /usr/src/app/wheels -r requirements.txt


#########
# FINAL #
#########

# pull official base image
FROM python:3.8-alpine

# create directory for the app user
RUN mkdir -p /home/itel

# create the app user
RUN addgroup -S itel && adduser -S itel -G itel

# create the appropriate directories
ENV APP_HOME=/home/itel
RUN mkdir $APP_HOME/static
RUN mkdir $APP_HOME/media
WORKDIR $APP_HOME

# install dependencies
RUN apk --update --upgrade --no-cache add gcc musl-dev mariadb-connector-c-dev libffi-dev cairo-dev pango-dev \
    fontconfig ttf-freefont font-noto terminus-font \
    && fc-cache -f \
    && fc-list | sort

# libpq tzdata
# jpeg-dev zlib-dev libjpeg
COPY --from=builder /usr/src/app/wheels /wheels
COPY --from=builder /usr/src/app/requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache /wheels/*

# copy entrypoint.sh
COPY ./entrypoint.sh $APP_HOME

# copy project
COPY . $APP_HOME

# chown all the files to the app user
RUN chown -R itel:itel $APP_HOME

# change to the app user
USER itel
