# Integration Checklist (Virtual + Physical)

Use this checklist before introducing HTTPS and broker.

## A. Canonical Services

- [x] Choose canonical gateway entrypoint (apps/gateway/main.py)
- [x] Mark legacy middleware.py as deprecated
- [x] Define service ports and URLs in one config file

## B. Runtime Modes

- [x] Add room mode field: virtual | physical
- [x] Gateway routes commands based on mode
- [ ] Frontend only calls gateway

## C. State Contract

- [x] Define canonical RoomState in shared/contracts
- [x] Define canonical HandState in shared/contracts
- [x] Define canonical Event envelope
- [x] Adapt virtual engine output to canonical contract
- [x] Adapt physical engine output to canonical contract

## D. Identity and Security Preparation

- [ ] Add session concept (room + player binding)
- [ ] Add token issuance and validation interfaces
- [ ] Add command authorization checks
- [ ] Add turn-ownership validation guard

## E. Broker Preparation

- [ ] Define topic names in one place
- [ ] Define publisher/subscriber interfaces
- [ ] Replace polling targets first: status and hand

## F. Frontend Integration

- [ ] Frontend subscribes to normalized events only
- [x] Frontend sends commands to one gateway endpoint family
- [ ] Remove frontend direct dependency on engine-specific payloads

## G. Regression Safety

- [ ] Keep old route names until frontend migration is complete
- [ ] Add basic integration tests for both room modes
- [ ] Add smoke test for rematch and role rotation in both modes
