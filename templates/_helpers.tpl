{{- define "airflow" -}}
apiVersion: extensions/v1beta1
kind: Deployment
metadata:
  name: {{ .name }}
spec:
  replicas: {{ .replicas | default 1 }}
  template:
    metadata:
      labels:
        app: airflow
        tier: {{ .name }}
    spec:
      restartPolicy: Always
      containers:
        - name: web
          image: gcr.io/{{ .projectId }}/airflow-gke:latest
          ports:
            - name: web
              containerPort: 8080
          volumeMounts:
          - name: dagbag
            mountPath: /git
          envFrom:
          - configMapRef:
              name: config-airflow
          {{- if eq .name "web" }}
          livenessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 60
            timeoutSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: 8080
            initialDelaySeconds: 60
            timeoutSeconds: 30
          {{- end }}
          command: ["/entrypoint.sh"]
          args:  {{ .commandArgs }}
        - name: git-sync
          image: gcr.io/google_containers/git-sync:v2.0.4
          volumeMounts:
          - name: dagbag
            mountPath: /git
          envFrom:
          - configMapRef:
              name: config-git-sync
      volumes:
        - name: dagbag
          emptyDir: {}
{{- end -}}
