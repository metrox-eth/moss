// Verbatim reviewed function bodies from MOSS_CORE_V07.ino
void serviceTx() {
  if (!Serial) {
    txHead = txTail = 0;
    return;
  }
  size_t n = (txHead + sizeof(txQueue) - txTail) % sizeof(txQueue);
  if (n > 64)
    n = 64;
  if (n > sizeof(txQueue) - txTail)
    n = sizeof(txQueue) - txTail;
  // Core 3.2.0 USBCDC::write can spin when its FIFO is full even with
  // timeout=0. TinyUSB's single write returns the accepted count; no retry and
  // no host-dependent wait.
  if (n) {
    uint32_t accepted = tud_cdc_n_write(0, txQueue + txTail, n);
    txTail = (txTail + accepted) % sizeof(txQueue);
    tud_cdc_n_write_flush(0);
  }
}

bool usbOpen() { return bool(Serial) && tud_mounted() && !tud_suspended(); }
