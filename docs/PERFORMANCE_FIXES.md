# Performance Fixes - Connection Pooling & Resource Optimization

## 🔴 Sorun: Yüksek Failure Rate (%48) ve Connection Reset Errors

### Tespit Edilen Sorunlar:

1. **Connection Pooling Eksikliği**
   - Her request'te yeni MySQL bağlantısı açılıyor
   - 1000 kullanıcı × 2 pod = binlerce bağlantı
   - MySQL `max_connections` limitine ulaşılıyor
   - `ConnectionResetError(54, 'Connection reset by peer')` hataları

2. **Düşük Pod Resource Limitleri**
   - CPU: 500m (0.5 core) - 1000 kullanıcı için çok az
   - Memory: 512Mi - connection pooling için yetersiz
   - Pod'lar CPU throttling'e giriyor
   - Response time'lar 30-120 saniyeye çıkıyor

3. **Yüksek Response Time'lar**
   - Bağlantı açma/kapama overhead'i
   - Pod'ların overload olması
   - Timeout'lar ve connection reset'ler

## ✅ Yapılan Düzeltmeler:

### 1. Connection Pooling Eklendi
- **Flask App**: PyMySQL connection pool (min=5, max=20 per pod)
- **Cloud Function**: Global connection pool (min=1, max=5)
- **Fayda**: Bağlantılar yeniden kullanılıyor, overhead azalıyor

### 2. Resource Limitleri Artırıldı
```yaml
resources:
  requests:
    cpu: 500m      # Önceki: 200m
    memory: 512Mi  # Önceki: 256Mi
  limits:
    cpu: 2000m     # Önceki: 500m (4x artış!)
    memory: 1Gi    # Önceki: 512Mi (2x artış!)
```

### 3. Connection Pool Ayarları
- **DB_POOL_MIN_SIZE**: 5 (her pod minimum 5 bağlantı tutar)
- **DB_POOL_MAX_SIZE**: 20 (her pod maksimum 20 bağlantı)
- **Toplam**: 2 pod × 20 = 40 maksimum bağlantı (MySQL limit'i altında)

## 🚀 Deployment Adımları:

### 1. Yeni Docker Image Build & Push
```bash
# Connection pooling kodunu içeren yeni image build et
docker build -t us-central1-docker.pkg.dev/url-shortener-479913/url-shortener-repo/url-shortener:latest -f docker/Dockerfile .
docker push us-central1-docker.pkg.dev/url-shortener-479913/url-shortener-repo/url-shortener:latest
```

### 2. ConfigMap Güncelle
```bash
kubectl apply -f k8s/configmap.yaml
```

### 3. Deployment Güncelle
```bash
kubectl apply -f k8s/deployment.yaml
kubectl rollout restart deployment url-shortener
```

### 4. Değişiklikleri Doğrula
```bash
# Pod'ların yeniden başladığını kontrol et
kubectl get pods -l app=url-shortener -w

# Log'larda connection pool mesajını gör
kubectl logs -l app=url-shortener | grep "connection pool initialized"

# Resource kullanımını kontrol et
kubectl top pods -l app=url-shortener
```

## 📊 Beklenen İyileştirmeler:

1. **Failure Rate**: %48 → %5-10 (beklenen)
2. **Response Time**: 30-120s → 100-500ms (beklenen)
3. **Throughput**: 8.5 RPS → 50-100+ RPS (beklenen)
4. **Connection Errors**: Connection reset errors → 0 (beklenen)

## 🧪 Test Senaryosu:

1. **Düşük Load Test** (100 kullanıcı):
   - Failure rate < %1 olmalı
   - Response time < 500ms olmalı

2. **Orta Load Test** (500 kullanıcı):
   - Failure rate < %5 olmalı
   - Response time < 1s olmalı
   - HPA pod'ları scale up etmeli

3. **Yüksek Load Test** (1000 kullanıcı):
   - Failure rate < %10 olmalı
   - Response time < 2s olmalı
   - Tüm pod'lar çalışır durumda olmalı

## ⚠️ Önemli Notlar:

1. **MySQL max_connections**: MySQL VM'de `max_connections` değerini kontrol edin:
   ```sql
   SHOW VARIABLES LIKE 'max_connections';
   ```
   En az 100 olmalı (2 pod × 20 + buffer = ~50 bağlantı kullanılacak)

2. **HPA Scaling**: HPA otomatik olarak pod sayısını artıracak, ama connection pool ayarları her pod için geçerli

3. **Monitoring**: Test sırasında şunları izleyin:
   - Pod CPU/Memory kullanımı
   - MySQL connection sayısı
   - Response time percentiles
   - Failure rate

## 🔍 Troubleshooting:

### Hala Connection Reset Errors Varsa:

1. **MySQL Connection Limit Kontrolü**:
   ```bash
   # MySQL VM'de
   mysql -u root -p
   SHOW VARIABLES LIKE 'max_connections';
   SHOW STATUS LIKE 'Threads_connected';
   ```

2. **Pod Log'larını Kontrol Et**:
   ```bash
   kubectl logs -l app=url-shortener --tail=100 | grep -i "connection\|pool\|error"
   ```

3. **Resource Kullanımını Kontrol Et**:
   ```bash
   kubectl top pods -l app=url-shortener
   # CPU veya Memory limit'ine ulaşıyorsa, limitleri daha da artır
   ```

4. **HPA Scaling Durumunu Kontrol Et**:
   ```bash
   kubectl get hpa url-shortener-hpa
   kubectl describe hpa url-shortener-hpa
   ```
