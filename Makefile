SALT_RELEASES := latest 2016.3 2015.8

TAGS ?= $(foreach TAG,$(UBUNTU_TAGS),$(addprefix $(TAG)-,$(SALT_RELEASES)))

EXTRA_TAGS += $(foreach TAG,$(UBUNTU_TAGS),$(TAG)=$(TAG)-latest) \
							$(foreach SALT_RELEASE,$(SALT_RELEASES),$(SALT_RELEASE)=latest-$(SALT_RELEASE))

include Makefile.docker

