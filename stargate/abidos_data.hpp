#ifndef ABIDOS_DATA_H
#define ABIDOS_DATA_H

#include <boost/foreach.hpp>

#include "abidos_common.hpp"

#include "abidos_type_encoding.hpp"
#include "abidos_byte_string.hpp"
#include "abidos_uuid.hpp"
#include "abidos_data_type.hpp"
#include "abidos_world_interface.hpp"

namespace abidos
{

class InstanceControlBlock;
   
typedef boost::intrusive_ptr<InstanceControlBlock> PInstanceControlBlock;
   
   
   
// This class does not allocate the memory for the bit arrays, it simply wraps
// a pointer with accessors. This class is intended to be passed by value.
class BitSet
{
   uint8_t  * m_pArray;
   uint16_t   m_numBits;
      
   BitSet();
  public:
   BitSet( uint16_t nNumBits, uint8_t * pArray ) : m_pArray(pArray), m_numBits(nNumBits)
   {}
      
   bool test( uint16_t idx ) const { (m_pArray[ idx / 8 ] & (1 << (idx % 8))); }
      
   void set( uint16_t idx )  { m_pArray[ idx / 8 ] |= 1 << (idx % 8);  }
      
   void clear() 
   {
      int nbytes = m_numBits/8 + m_numBits%8 ? 1 : 0;
      for( uint16_t i=0; i < nbytes; i++ )
         m_pArray[i] = 0;
   }
      
   class Iter
   {
      const uint8_t * parr;
      uint16_t        nbits;
      uint16_t        count;
         
      friend class BitSet;
         
      Iter( const uint8_t * p, uint16_t numbits ) : parr(p), nbits(numbits), count(0)
      {}
         
     public:        
      // Returns -1 after all set indicies have been returned
      int next()
      {
         while( count <= nbits )
         {
            if ( parr[ count / 8 ] & (1 << (count%8)) )
               return count++;
            else
               ++count;
         }
         return -1;
      }
   };
      
   Iter iterate() const { return Iter(m_pArray, m_numBits); }
};


class InstanceControlBlock : public sg::ReferenceCounted, boost::noncopyable
{
   typedef std::vector< WorldInterface * >  WatchersVector;
   typedef std::list< ByteString *  >       StringList;
   typedef std::list< UUID       *  >       UUIDList;
   
   DataType       *m_pType;
   uint8_t        *m_pData;
   uint16_t        m_numVars;

   WorldInterface *m_pOwningInterface;

   UUID            m_uuid;       // Unique ID for this instance
   
   WatchersVector  m_watchers;   // List of WorldInterfaces that are monitoring
                                 // this instance
      
   StringList      m_stringList; // Strings & UUIDs are referenced by pointer
   UUIDList        m_uuidList;   // in the data block. Hold references to them
                                 // here so they can be deleted when the instance is
                                 // destroyed.
   bool            m_bModified;  // True if any data within the instance is modified
      
   uint8_t * getBitSet( int index ) 
   {
      return ((uint8_t*) &this[1]) + (m_numVars/8 + m_numVars%8 ? 1:0) * index;
   }
      
      
  public:
      
   inline static std::size_t requiredSize( DataType *pt )
   {
      uint16_t nvars = pt->getTotalNumVars();
      return sizeof(InstanceControlBlock) + (nvars/8 + (nvars%8 ? 1:0)) * 3;
   }
      
   // NOTE: This class must be allocated via placement new. The size
   // requirement is:
   //    InstanceControlBlock::requiredSize( <data type> );
   // 
   // The bitset arrays trail the control block instance for locality of reference
   // reasons
   InstanceControlBlock( WorldInterface * pIface, DataType * pType, uint8_t * pData );
      
   ~InstanceControlBlock();
      
   virtual void onZeroRefcount();

   WorldInterface * getOwningInterface() { return m_pOwningInterface; }
   void             setOwningInterface( WorldInterface * pwi ) { m_pOwningInterface = pwi; }

   World * world() { m_pOwningInterface->world(); }

   const UUID * uuid() { return &m_uuid; }
   
   DataType * dataType() { return m_pType; }
   uint8_t  * data()     { return m_pData; }
      
   BitSet  validSet()    { return  BitSet( m_numVars, getBitSet(0) ); }
   BitSet  updatedSet()  { return  BitSet( m_numVars, getBitSet(1) ); }
   BitSet  callbackSet() { return  BitSet( m_numVars, getBitSet(2) ); }

   

   void setModified()
   {
      if ( !m_bModified )
      {
         m_bModified = true;
         BOOST_FOREACH( WorldInterface * pwi, m_watchers )
         {
            pwi->objectUpdated( &m_uuid );
         }
      }
   }

   void clearModifiedFlag() { m_bModified = false; }
            
   ByteString * allocByteString() 
   {
      ByteString * pbs = new ByteString;
      m_stringList.push_back( pbs );
      return pbs;
   }
      
   UUID * allocUUID()
   {
      UUID * p = new UUID;
      m_uuidList.push_back( p );
      return p;
   }
};
   
   

class Instance : public sg::Instance
{
   mutable PInstanceControlBlock   m_cblock;
   const TypeEncoding             *m_pEncoding;

   // used by World to cache Instance objects in
   // a single-linked list. Instances of this class are created
   // and destroyed very quickly. We mitigate this by caching
   // instances.
   union
   {
      uint8_t                     *m_pData;
      Instance                    *m_pNext; 
   };

   uint16_t                        m_cblockVarOffset;

   
   friend class World; // give World access to m_pNext & Instance constructor

   Instance() :
         m_cblock(0), m_pEncoding(0), m_pData(0), m_cblockVarOffset(0)
   {};

   ~Instance() {}

   // ---- Setters ----
   
   template <class T> T * get( const sg::AttributeID & aid ) const
   {
      return (T*)( m_pData + m_pEncoding->getVariable( aid ).byteOffset );
   }
      
   template <class T> void set( const sg::AttributeID & aid, const T & value )
   {
      TypeEncoding::VarInfo vi = m_pEncoding->getVariable( aid );
      *get<T>(aid) = value;
      m_cblock->validSet().set  ( m_cblockVarOffset + vi.linearIndexOffset );
      m_cblock->updatedSet().set( m_cblockVarOffset + vi.linearIndexOffset );
      m_cblock->setModified();
   }
      
   void set_uuid( const sg::AttributeID & aid, const UUID * value )
   {
      TypeEncoding::VarInfo vi = m_pEncoding->getVariable( aid );
          
      m_cblock->validSet().set  ( m_cblockVarOffset + vi.linearIndexOffset );
      m_cblock->updatedSet().set( m_cblockVarOffset + vi.linearIndexOffset );
          
      UUID **pp = get<UUID*>(aid);
          
      if (!*pp)
         *pp = m_cblock->allocUUID();
          
      if (value)
         **pp = *value;
      else
         (*pp)->zero();

      m_cblock->setModified();
   }
      
   ByteString * update_string( const sg::AttributeID & aid )
   {
      TypeEncoding::VarInfo vi = m_pEncoding->getVariable( aid );
      ByteString ** ppbs = get<ByteString*>(aid);
      m_cblock->validSet().set  ( m_cblockVarOffset + vi.linearIndexOffset );
      m_cblock->updatedSet().set( m_cblockVarOffset + vi.linearIndexOffset );
      if (!*ppbs) 
         *ppbs = m_cblock->allocByteString();

      m_cblock->setModified();
      return *ppbs;
   }
      
  public:

   void onZeroRefcount();
     
   void reset( PInstanceControlBlock cb, const TypeEncoding * penc, uint8_t *pdat, uint16_t voff )
   {
      m_cblock          = cb;
      m_pEncoding       = penc;
      m_pData           = pdat;
      m_cblockVarOffset = voff;
   };
      
   DataType * getType() const { return m_pEncoding->dataType(); }

   sg::BasicType getAttributeType( const sg::AttributeID & attrId ) const;
      
   // debugging only
   uint32_t getByteOffset( const sg::AttributeID & aid )
   {
      return m_pEncoding->getVariable( aid ).byteOffset;
   }
      
   uint8_t * getDataBlock() { return m_pData; }
                  
   //---------------------------------------------------------------------------------
   // Data get/set
   //
   bool               getBoolean    ( const sg::AttributeID & attrId ) const;
   int32_t            getInt32      ( const sg::AttributeID & attrId ) const;
   uint32_t           getUInt32     ( const sg::AttributeID & attrId ) const;
      
   int64_t            getInt64      ( const sg::AttributeID & attrId ) const;
   uint64_t           getUInt64     ( const sg::AttributeID & attrId ) const;
       
   float              getFloat      ( const sg::AttributeID & attrId ) const;
   double             getDouble     ( const sg::AttributeID & attrId ) const;
      
   const ByteString * getByteString ( const sg::AttributeID & attrId ) const;
   const UUID       * getUUID       ( const sg::AttributeID & attrId ) const;
   sg::PInstance      getInstance   ( const sg::AttributeID & attrId ) const;
      
      
   void  setBoolean    ( const sg::AttributeID & attrId, bool     value );
   void  setInt32      ( const sg::AttributeID & attrId, int32_t  value );
   void  setUInt32     ( const sg::AttributeID & attrId, uint32_t value );
       
   void  setInt64      ( const sg::AttributeID & attrId, int64_t  value );
   void  setUInt64     ( const sg::AttributeID & attrId, uint64_t value );
       
   void  setFloat      ( const sg::AttributeID & attrId, float    value );
   void  setDouble     ( const sg::AttributeID & attrId, double   value );

   void  setByteString ( const sg::AttributeID & attrId, const sg::ByteString * value );   
   void  setByteString ( const sg::AttributeID & attrId, const ByteString     * value );
   void  setByteString ( const sg::AttributeID & attrId, const std::string    & value );
   void  setByteString ( const sg::AttributeID & attrId, const char           * value );
   void  setByteString ( const sg::AttributeID & attrId, const uint8_t        * value, std::size_t nBytes );

   void  setUUID       ( const sg::AttributeID & attrId, const sg::UUID * value );
   void  setUUID       ( const sg::AttributeID & attrId, const UUID     * value );
};
   
   

} // end namespace abidos


#endif

