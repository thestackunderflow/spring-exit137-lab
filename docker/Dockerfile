# One stage, exec form (java is PID 1). No memory flag in the image: the flags come from JAVA_TOOL_OPTIONS in Compose.
# A JDK (not a JRE) so jcmd exists; curl is in this image too.
FROM eclipse-temurin:21.0.12.1_1-jdk-noble@sha256:107215954359f1ab0be058a247d7c64ed6e69c71c1682d471d38ef751ec8e964
COPY target/app.jar /app.jar
ENTRYPOINT ["java", "-jar", "/app.jar"]
