FROM node:22-alpine AS build
WORKDIR /app
ARG MOVON_API_ORIGIN
ENV MOVON_API_ORIGIN=${MOVON_API_ORIGIN}
# Menyalakan guard prebuild: build gagal bila MOVON_API_ORIGIN kosong, bukan proxy senyap ke localhost.
ENV CI=1
# Picker akun demo: kosong = mati (D1). Dibaca saat build, jadi mengubahnya butuh redeploy, dan kredensial demo ikut masuk bundle publik.
ARG NEXT_PUBLIC_DEMO_ACCOUNTS
ENV NEXT_PUBLIC_DEMO_ACCOUNTS=${NEXT_PUBLIC_DEMO_ACCOUNTS}
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
ENV HOSTNAME=0.0.0.0
USER node
EXPOSE 3000
CMD ["node","server.js"]
