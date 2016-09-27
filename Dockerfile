FROM trevorj/boilerplate
MAINTAINER Trevor Joynson "<docker@trevor.joynson.io>"

ENV STATE_ROOT=$IMAGE_ROOT/states \
    PILLAR_ROOT=$IMAGE_ROOT/pillar \
    LAYERS_ROOT=$IMAGE_ROOT/layers

RUN set -exv \
 && echo "Installing Salt packages" \
 && lazy-apt --no-install-recommends \
      # Salt minion
      python-apt salt-minion \
      \
      # Needed at runtime by pyopenssl for exxo build of salt-apply-state-layer
      # libssl1.0.0 \
 && :

ADD build.d $IMAGE_ROOT/build.d
RUN run-parts --verbose --exit-on-error "$IMAGE_ROOT/build.d"\
 && rm -rf "$IMAGE_ROOT/build.d"

ADD image $IMAGE_ROOT/

# >> Let them do this one, honey.
#USER $APP_USER

