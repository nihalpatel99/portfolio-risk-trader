let nextRowId = 1

export function makeEmptyHolding() {
  return { id: nextRowId++, ticker: '', quantity: '', price: '' }
}
