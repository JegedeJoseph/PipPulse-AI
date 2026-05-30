# PipPulse AI - Quick Reference Checklist
**Last Updated**: May 30, 2026 | **Current Phase**: Pre-Blocker Mitigation

---

## 🛑 CRITICAL BLOCKERS (Fix First)

### BLOCKER 1: FinBERT Accuracy Validation
- [ ] Download FiQA dataset
- [ ] Download FinancialPhraseBank dataset
- [ ] Create `backend/eval/finbert_benchmark.py`
- [ ] Run benchmark on FiQA
- [ ] Run benchmark on FinancialPhraseBank
- [ ] Check F1-score ≥75%
- [ ] Generate confusion matrix
- [ ] Document results in `backend/eval/finbert_benchmark_results.md`
- **Target**: F1-score ≥75% | **By**: Day 3 | **Owner**: ML Eng

### BLOCKER 2: End-to-End Latency Measurement
- [ ] Add timestamp tracking to all components
- [ ] Create `backend/app/utils/latency_tracker.py`
- [ ] Modify news schema to include latency tracking
- [ ] Create `backend/tests/synthetic_news_generator.py`
- [ ] Create `backend/tests/test_latency.py`
- [ ] Run synthetic latency test
- [ ] Measure P50, P95, P99 latencies
- [ ] If P95 >5s: optimize (batch, quantize, cache)
- [ ] Generate report in `backend/eval/latency_report.json`
- **Target**: P95 ≤5s | **By**: Day 5 | **Owner**: Backend Eng

### BLOCKER 3: Load Testing at 1000 items/minute
- [ ] Create `backend/tests/load_test.py`
- [ ] Create `backend/tests/load_generator.py`
- [ ] Modify collectors for Redis input testing
- [ ] Run 5-minute load test
- [ ] Monitor metrics (CPU, memory, DB connections)
- [ ] If fails: identify bottleneck
- [ ] Implement optimization
- [ ] Run 10-minute load test
- [ ] Generate report in `backend/eval/load_test_report.md`
- **Target**: 1000 items/min, 0% error rate | **By**: Day 8 | **Owner**: DevOps

### BLOCKER 4: Admin Panel Wire-Up
- [ ] Create/modify `backend/app/api/admin.py` endpoints
  - [ ] `POST /admin/config/thresholds`
  - [ ] `POST /admin/config/weights`
  - [ ] `POST /admin/config/windows`
  - [ ] `GET /admin/config`
- [ ] Create PostgreSQL migration for config tables
- [ ] Run migration: `alembic upgrade head`
- [ ] Create `frontend/src/components/AdminPanel.tsx`
- [ ] Wire form inputs to API calls
- [ ] Add success/error notifications
- [ ] Test end-to-end: adjust config → signal regenerated → persisted
- **Target**: Fully functional admin panel | **By**: Day 10 | **Owner**: Backend + Frontend

---

## ✅ WEEK 1 VALIDATION TESTS

### Day 1-3: FinBERT Accuracy
```bash
# Run benchmark
python backend/eval/finbert_benchmark.py --dataset fiqua
python backend/eval/finbert_benchmark.py --dataset financialphrase

# Check results
cat backend/eval/finbert_benchmark_results.md
```

### Day 4-5: Latency Measurement
```bash
# Run latency test
pytest backend/tests/test_latency.py -v

# View results
cat backend/eval/latency_report.json
```

### Day 6-8: Load Test
```bash
# Run load test
python backend/tests/load_test.py --duration 300 --rate 1000

# Monitor in separate terminal
docker stats pippulse-backend pippulse-mongodb pippulse-redis

# View report
cat backend/eval/load_test_report.md
```

---

## 📋 DAILY STANDUP TEMPLATE

```
DATE: YYYY-MM-DD | PHASE: [Week 1/2/3/4]

COMPLETED:
- [ ] Task A
- [ ] Task B

IN PROGRESS:
- [ ] Task C (70%)

BLOCKED BY:
- [ ] Issue X

METRICS:
- Code coverage: ___%
- Tests passing: ___%
- FinBERT accuracy: ___%
- E2E latency P95: ___ms
- Load test throughput: ___items/min

NEXT 24 HOURS:
- [ ] Plan 1
- [ ] Plan 2

RISKS/CONCERNS:
- [List any]

SIGN-OFF: ___________ [Name]
```

---

## 🧪 TEST EXECUTION CHECKLIST

### Run All Tests
```bash
cd backend

# Install test dependencies
pip install -r requirements-test.txt

# Run all tests with coverage
pytest tests/ -v --cov=app --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Test Coverage Goals
- [ ] Week 1: >20%
- [ ] Week 2: >40%
- [ ] Week 3: >70%
- [ ] Week 4: >90%

---

## 🚀 DEPLOYMENT CHECKLIST

### Pre-Deployment (Day 30)
- [ ] All 500+ tests passing
- [ ] Coverage >90%
- [ ] All 10 acceptance criteria verified
- [ ] Documentation complete
- [ ] Code review approved
- [ ] No critical issues open

### Deployment
```bash
# Start services
docker-compose up -d --build

# Wait for health
docker-compose ps

# Verify endpoints
curl http://localhost:8000/health/
curl http://localhost:3000/

# Test WebSocket
wscat -c ws://localhost:8000/ws/

# View logs
docker-compose logs -f backend
```

### Post-Deployment
- [ ] All services healthy
- [ ] API responding
- [ ] WebSocket connected
- [ ] Dashboard live
- [ ] No error logs

---

## 📊 SUCCESS METRICS TRACKING

### Accuracy (Target: ≥75% F1-score)
```
Week 1: ___% (FiQA)
Week 1: ___% (FinancialPhraseBank)
Status: ✅ / ❌ / 🔄
```

### Performance (Target: P95 ≤5s)
```
Week 1: ___ms (after optimization)
Status: ✅ / ❌ / 🔄
```

### Throughput (Target: 1000 items/min, 0% error)
```
Week 1: ___ items/min processed
Week 1: ___ % error rate
Status: ✅ / ❌ / 🔄
```

### Testing (Target: >90% coverage)
```
Week 1: __% coverage
Week 2: __% coverage
Week 3: __% coverage
Week 4: __% coverage
Status: 🔄
```

### PRD Acceptance (Target: 10/10)
```
AC-1: ✅ / ❌
AC-2: ✅ / ❌
AC-3: ✅ / ❌
AC-4: ✅ / ❌
AC-5: ✅ / ❌
AC-6: ✅ / ❌
AC-7: ✅ / ❌
AC-8: ✅ / ❌
AC-9: ✅ / ❌
AC-10: ✅ / ❌
Total: __/10
```

---

## 🔗 IMPORTANT FILES & PATHS

```
Project Root: f:/Users/USER/Gr8ness/PipPulse AI/

Backend:
- backend/app/main.py                    [FastAPI entry point]
- backend/app/api/                       [API endpoints]
- backend/app/sentiment/engine.py        [FinBERT inference]
- backend/app/signal/generator.py        [Signal generation]
- backend/app/collectors/                [Data collection]
- backend/app/preprocessing/pipeline.py  [Text preprocessing]
- backend/app/backtesting/engine.py      [Backtesting]
- backend/requirements.txt                [Dependencies]
- backend/requirements-test.txt           [Test dependencies]

Frontend:
- frontend/src/app/                      [Next.js app]
- frontend/src/components/               [React components]
- frontend/src/pages/                    [Pages]
- frontend/package.json                  [Dependencies]

Docker:
- docker-compose.yml                     [Multi-service setup]
- docker/mongodb/                        [MongoDB config]
- docker/postgres/                       [PostgreSQL config]
- docker/influxdb/                       [InfluxDB config]

Documentation:
- PROJECT_STATUS_AUDIT.md                [Detailed audit]
- PRODUCTION_READINESS_PLAN.md           [4-week plan]
- EXECUTIVE_SUMMARY.md                   [High-level overview]
- DEPLOYMENT.md                          [Deployment guide]
- OPERATIONS.md                          [Operations guide]
- Ayodeji_FYP_PRD.txt                    [PRD from Prof]

Evaluation:
- backend/eval/finbert_benchmark.py      [FinBERT accuracy]
- backend/eval/latency_tracker.py        [Latency measurement]
- backend/tests/load_test.py             [Load testing]
```

---

## 🔧 COMMON COMMANDS

### Start Services
```bash
cd /path/to/PipPulse\ AI
docker-compose up -d
docker-compose ps
```

### Stop Services
```bash
docker-compose down
docker-compose down -v  # Remove volumes (WARNING: deletes data)
```

### View Logs
```bash
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs signal-engine | grep ERROR
```

### Run Tests
```bash
cd backend
pytest tests/ -v
pytest tests/collectors/ -v --cov
pytest tests/ -k "websocket" -v
```

### Access Services
```
Backend API: http://localhost:8000
API Docs: http://localhost:8000/docs
Frontend: http://localhost:3000
MongoDB: mongodb://localhost:27017
Redis: localhost:6379
PostgreSQL: localhost:5432
InfluxDB: http://localhost:8086
```

### Database Access
```bash
# MongoDB
docker-compose exec mongodb mongosh

# PostgreSQL
docker-compose exec postgres psql -U pippulse -d pippulse

# Redis
docker-compose exec redis redis-cli

# InfluxDB
docker-compose exec influxdb influx
```

---

## ⚠️ COMMON ISSUES & FIXES

### Service Won't Start
```bash
# Check logs
docker-compose logs [service-name]

# Check port conflicts
netstat -an | grep 8000

# Clean restart
docker-compose down -v
docker-compose up -d
```

### Tests Failing
```bash
# Reinstall dependencies
pip install -r requirements.txt -r requirements-test.txt

# Clear pytest cache
pytest --cache-clear

# Run with verbose output
pytest -vv -s
```

### Memory Issues
```bash
# Check Docker resource usage
docker stats

# Increase Docker memory limit in Docker Desktop settings
# Restart services
docker-compose restart
```

### Database Connection Errors
```bash
# Verify service is healthy
docker-compose ps

# Wait for service startup (health check)
sleep 10
docker-compose ps

# Check connection details in .env
cat .env | grep MONGO
cat .env | grep POSTGRES
```

---

## 📅 MILESTONE DATES

| Week | Milestone | Status |
|------|-----------|--------|
| W1 (May 30-Jun 6) | ✋ Blockers fixed: Accuracy, Latency, Load test, Admin | [ ] |
| W2 (Jun 7-13) | ✅ 250+ tests, 40% coverage, Admin functional | [ ] |
| W3 (Jun 14-20) | ✅ 400+ tests, 70% coverage, E2E validated | [ ] |
| W4 (Jun 21-27) | ✅ 500+ tests, 90% coverage, All docs complete | [ ] |
| **SUBMISSION** | **Jun 30, 2026** | [ ] |

---

## 👥 TEAM ROLES & RESPONSIBILITIES

| Role | Name | Responsibilities |
|------|------|------------------|
| **ML Engineer** | TBD | FinBERT benchmark, backtesting validation, threshold calibration |
| **Backend Engineer** | TBD | Admin panel, API tests, performance optimization |
| **Frontend Engineer** | TBD | Admin UI, UX polish, responsive design |
| **QA/DevOps** | TBD | Test suite, load testing, documentation |
| **Project Manager** | TBD | Daily tracking, blocker resolution, sign-offs |

---

## 🎯 DEFINITION OF DONE

A task is "done" when:
- [ ] Code written and peer-reviewed
- [ ] Tests passing (100% of related tests)
- [ ] Coverage improved (documented delta)
- [ ] Documentation updated
- [ ] No console errors or warnings
- [ ] Acceptance criteria met

---

## 📞 ESCALATION PATH

**Blocker Found?**
1. Document issue with: what, why, impact
2. Report to Project Manager immediately
3. If needs decision: escalate to Tech Lead
4. If architectural: escalate to Lead Engineer/Supervisor
5. If timeline risk: escalate to Project Manager + Supervisor

---

## 🎉 FINAL SUCCESS CRITERIA

✅ **System passes all 10 PRD acceptance criteria**
✅ **90%+ test coverage**
✅ **FinBERT ≥75% F1-score**
✅ **E2E latency P95 ≤5 seconds**
✅ **Handles 1000 items/minute**
✅ **Complete documentation**
✅ **No critical issues**
✅ **Ready for production**

---

**Print this and keep on your desk!**

---

Last updated: May 30, 2026
