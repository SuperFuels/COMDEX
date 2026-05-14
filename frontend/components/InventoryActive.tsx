import ProductCard from './ProductCard'

export default function InventoryActive({ products }:{products:any[]}) {
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {products.map(p=> <ProductCard key={p.id} product={p}/>)}
    </div>
  )
}
