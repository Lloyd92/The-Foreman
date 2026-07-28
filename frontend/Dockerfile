FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html
COPY styles.css /usr/share/nginx/html/styles.css
COPY app.js /usr/share/nginx/html/app.js
COPY manifest.webmanifest /usr/share/nginx/html/manifest.webmanifest
COPY assets /usr/share/nginx/html/assets
COPY pages /usr/share/nginx/html/pages
COPY utils /usr/share/nginx/html/utils
COPY default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
