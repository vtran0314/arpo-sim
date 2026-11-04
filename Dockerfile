ARG ROS_DISTRO=humble
FROM osrf/ros:${ROS_DISTRO}-desktop

ARG ROS_DISTRO
ARG HOST_UID=1000
ARG HOST_GID=1000
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
      ros-${ROS_DISTRO}-ros-gz \
      ros-dev-tools \
      python3-colcon-common-extensions \
      mesa-utils \
      git vim sudo \
    && rm -rf /var/lib/apt/lists/*

# Ubuntu 24.04 images ship a default "ubuntu" user at UID 1000; remove it
# so the host UID can be reused.
RUN userdel -r ubuntu 2>/dev/null || true \
 && groupadd -g ${HOST_GID} dev \
 && useradd -m -u ${HOST_UID} -g ${HOST_GID} -s /bin/bash dev \
 && echo "dev ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dev

USER dev
WORKDIR /home/dev/ws
RUN echo "source /opt/ros/${ROS_DISTRO}/setup.bash" >> ~/.bashrc \
 && echo "[ -f ~/ws/install/setup.bash ] && source ~/ws/install/setup.bash" >> ~/.bashrc

COPY --chown=dev:dev entrypoint.sh /home/dev/entrypoint.sh
RUN chmod +x /home/dev/entrypoint.sh
ENTRYPOINT ["/home/dev/entrypoint.sh"]
CMD ["bash"]
