#include <string.h>
#include <boost/lexical_cast.hpp>
#include <boost/foreach.hpp>

#include "abidos_data.hpp"


namespace abidos
{

using std::cerr;
using std::endl;

namespace
{
const char * get_default( DataType * pDt, int varNum )
{
   PCharStarMap m = pDt->getVars()[ varNum ].extraInfo;
          
   CharStarMap::iterator i = m->find( "default" );
          
   if ( i == m->end() )
      return 0;
   else
      return i->second;
}
      
double default_num( DataType * pDt, int varNum )
{
   double       n = 0;
   const char * p = 0;
          
   try
   {
      p = get_default( pDt, varNum );
      if (p)
         n = boost::lexical_cast<double>(p);
   }
   catch( boost::bad_lexical_cast )
   {
      cerr << "Invalid numeric default: " << p << endl;
      assert(0);
   }
          
   return n;
}
      
bool default_bool( DataType *pDt, int varNum )
{
   const char * p = get_default( pDt, varNum );
          
   return p && strcmp(p,"true") == 0;
}
              
      
const char * default_string( DataType *pDt, int varNum )
{
   const char * p = get_default( pDt, varNum );
   return p ? p : "";
}
      
      
void init_defaults( sg::PInstance & pinst, std::string indent = "" )
{
   Instance                * i = static_cast<Instance *>(pinst.get());
   int                       x = 0;
   std::vector< DataType * > dtvec;
   const TypeEncoding       *pte = i->getType()->getEncoding();
          
   //cerr << indent << "Init Instance: " << std::hex << (void*)(i->getDataBlock());
   //cerr << " end: " << (void*)(i->getDataBlock() + pte->getFullInheritanceStaticSize()) << std::dec << endl;
          
   for( x=0; x< pte->numInheritedClasses(); x++ )
   {
      dtvec.push_back( pte->baseClass(x)->m_pDataType );
   }
          
   dtvec.push_back( i->getType() );
          
   BOOST_FOREACH( DataType * pdt, dtvec )
   {
      int deriv     = pdt->getEncoding()->numInheritedClasses();
      int numvars   = pdt->getNumVars();
              
      //cerr << indent << "    ------ Init: " << pdt->getName() << " nderiv: " << deriv << " nvars: " << numvars << endl;
              
      for( x=0; x < numvars; x++ )
      {
         sg::AttributeID aid( deriv, x );

         const VarInfo * pvi = &pdt->getVars()[ x ];
                  
         //cerr << indent << "        var: " << pvi->pszName << " offset: " << i->getByteOffset(aid) << endl;
                  
         if ( pvi->bIsBasicType )
         {
            switch( pvi->tinfo.basicType )
            {
             case sg::TBOOL        : i->setBoolean   ( aid,            default_bool(pdt, x) ); break;
             case sg::TINT32       : i->setInt32     ( aid, (int32_t)  default_num(pdt, x)); break;
             case sg::TUINT32      : i->setUInt32    ( aid, (uint32_t) default_num(pdt, x)); break;
             case sg::TINT64       : i->setInt64     ( aid, (int64_t)  default_num(pdt, x)); break;
             case sg::TUINT64      : i->setUInt64    ( aid, (uint64_t) default_num(pdt, x)); break;
             case sg::TFLOAT       : i->setFloat     ( aid, (float)    default_num(pdt, x)); break;
             case sg::TDOUBLE      : i->setDouble    ( aid,            default_num(pdt, x)); break;
             case sg::TBYTE_STRING : i->setByteString( aid,            default_string(pdt, x)); break;
             case sg::TUUID        : i->setUUID      ( aid, (UUID*)0 ); break;
             default:
                assert(0);
            }
         }
         else
         {
            sg::PInstance isub = i->getInstance(aid);
            init_defaults( isub, indent + "   " );
         }
      }
   }
}
      
}// end anonymous namespace
   
//-----------------------------------------------------------------------------
   
InstanceControlBlock::InstanceControlBlock( WorldInterface * pIface, DataType * pType, uint8_t * pData ) :
      m_pType(pType),
      m_pData(pData),
      m_numVars( pType->getTotalNumVars() ),
      m_pOwningInterface( pIface ),
      m_bModified(false)
{
   m_uuid.setUniqueValue();
   
   sg::PInstance i = m_pOwningInterface->world()->allocateInstance(this, dataType()->getEncoding(), pData, 0);
       
   init_defaults( i );
}
   
InstanceControlBlock::~InstanceControlBlock()
{
   cerr << "~~~~ Control block destructor" << endl;
       
   BOOST_FOREACH( ByteString * p, m_stringList )
   {
      delete p;
   }

   BOOST_FOREACH( UUID * p, m_uuidList )
   {
      delete p;
   }
}
      
void InstanceControlBlock::onZeroRefcount()
{}

//-----------------------------------------------------------------------------
void Instance::onZeroRefcount()
{
//   cerr << "Instance zero refcount!" << endl;
   m_cblock->world()->deallocateInstance( this );
}

      
sg::BasicType Instance::getAttributeType( const sg::AttributeID & attrId ) const
{
   TypeEncoding::VarInfo vi = m_pEncoding->getVariable( attrId );
   return vi.typeCode < sg::MAX_BASIC_TYPE ? (sg::BasicType) vi.typeCode : sg::TINSTANCE;
}      
      
bool            Instance::getBoolean    ( const sg::AttributeID & attrId ) const 
{
   return *get<bool>(attrId);
}
   
int32_t         Instance::getInt32      ( const sg::AttributeID & attrId ) const 
{
   return *get<int32_t>(attrId);
}
   
uint32_t        Instance::getUInt32     ( const sg::AttributeID & attrId ) const 
{
   return *get<uint32_t>(attrId);
}
   
int64_t         Instance::getInt64      ( const sg::AttributeID & attrId ) const 
{
   return *get<int64_t>(attrId);
}
   
uint64_t        Instance::getUInt64     ( const sg::AttributeID & attrId ) const 
{
   return *get<uint64_t>(attrId);
}
   
   
float           Instance::getFloat      ( const sg::AttributeID & attrId ) const 
{
   return *get<float>(attrId);
}
   
double          Instance::getDouble     ( const sg::AttributeID & attrId ) const 
{
   return *get<double>(attrId);
}
      
const ByteString *    Instance::getByteString ( const sg::AttributeID & attrId ) const
{
   return *get<ByteString*>(attrId);
}
   
const UUID *          Instance::getUUID       ( const sg::AttributeID & attrId ) const
{
   return *get<UUID*>(attrId);
}
   
sg::PInstance       Instance::getInstance   ( const sg::AttributeID & attrId ) const
{
   TypeEncoding::VarInfo vi = m_pEncoding->getVariable( attrId );
   return m_cblock->world()->allocateInstance( m_cblock, 
                                               m_pEncoding->getVariableEncoding( vi ), 
                                               m_pData + vi.byteOffset,
                                               m_cblockVarOffset + vi.linearIndexOffset );
}
   
      
void  Instance::setBoolean    ( const sg::AttributeID & attrId, bool     value )
{ set(attrId,value); }
void  Instance::setInt32      ( const sg::AttributeID & attrId, int32_t  value )
{ set(attrId,value); }
void  Instance::setUInt32     ( const sg::AttributeID & attrId, uint32_t value )
{ set(attrId,value); }   
void  Instance::setInt64      ( const sg::AttributeID & attrId, int64_t  value )
{ set(attrId,value); }
void  Instance::setUInt64     ( const sg::AttributeID & attrId, uint64_t value )
{ set(attrId,value); }  
void  Instance::setFloat      ( const sg::AttributeID & attrId, float    value )
{ set(attrId,value); }
void  Instance::setDouble     ( const sg::AttributeID & attrId, double   value )
{ set(attrId,value); }
void  setByteString ( const sg::AttributeID & attrId, const sg::ByteString * value )
{ setByteString( attrId, static_cast<const ByteString*>(value) ); }
void  Instance::setByteString ( const sg::AttributeID & attrId, const sg::ByteString * value )
{update_string(attrId)->assign(value->data(), value->length()); }
void  Instance::setByteString ( const sg::AttributeID & attrId, const std::string & value )
{update_string(attrId)->assign(value); }      
void  Instance::setByteString ( const sg::AttributeID & attrId, const char        * value )
{update_string(attrId)->assign(value); }
void  Instance::setByteString ( const sg::AttributeID & attrId, const uint8_t     * value, std::size_t nBytes )
{update_string(attrId)->assign(value, nBytes); }
void  Instance::setUUID       ( const sg::AttributeID & attrId, const sg::UUID    * value )
{ set_uuid(attrId,static_cast<const UUID*>(value)); }
void  Instance::setUUID       ( const sg::AttributeID & attrId, const UUID        * value )
{ set_uuid(attrId,value); }

   
} // end namespace abidos

