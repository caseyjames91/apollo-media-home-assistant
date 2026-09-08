FROM eclipse-temurin:17-jdk
ARG CMDLINE_TOOLS=11076708
ARG GRADLE_VERSION=8.7
ENV ANDROID_SDK_ROOT=/opt/android-sdk
ENV PATH=$PATH:/opt/gradle/bin:$ANDROID_SDK_ROOT/cmdline-tools/latest/bin:$ANDROID_SDK_ROOT/platform-tools
RUN apt-get update && apt-get install -y --no-install-recommends wget unzip ca-certificates && rm -rf /var/lib/apt/lists/* \
 && wget -q https://services.gradle.org/distributions/gradle-${GRADLE_VERSION}-bin.zip -O /tmp/gradle.zip \
 && unzip -q /tmp/gradle.zip -d /opt \
 && ln -s /opt/gradle-${GRADLE_VERSION} /opt/gradle \
 && mkdir -p $ANDROID_SDK_ROOT/cmdline-tools \
 && wget -q https://dl.google.com/android/repository/commandlinetools-linux-${CMDLINE_TOOLS}_latest.zip -O /tmp/tools.zip \
 && unzip -q /tmp/tools.zip -d /tmp/cmdline \
 && mv /tmp/cmdline/cmdline-tools $ANDROID_SDK_ROOT/cmdline-tools/latest \
 && yes | sdkmanager --licenses >/dev/null \
 && sdkmanager 'platforms;android-35' 'build-tools;35.0.0' 'platform-tools' >/dev/null
WORKDIR /src
CMD ["gradle", "--no-daemon", ":app:assembleDebug"]
