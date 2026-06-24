# Use lightweight official Nginx image
FROM nginx:alpine

# Remove default site configuration
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy global Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy application virtual hosts
COPY conf.d/ /etc/nginx/conf.d/

# Expose HTTP port
EXPOSE 80

# Start Nginx in foreground mode
CMD ["nginx", "-g", "daemon off;"]