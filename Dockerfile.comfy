ARG AWS_REGION
FROM 366590864501.dkr.ecr.$AWS_REGION.amazonaws.com/esd-inference:dev

# TODO BYOC
#RUN apt-get update -y && \
#    apt-get install ffmpeg -y && \
#    rm -rf /var/lib/apt/lists/* \

COPY build_scripts/inference/start.sh /
RUN chmod +x /start.sh
