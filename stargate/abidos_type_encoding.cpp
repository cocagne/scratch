#include <iostream>
#include <string.h>
#include <vector>
#include <boost/foreach.hpp>

#include "abidos_type_encoding.hpp"
#include "abidos_data_type.hpp"

namespace abidos
{
using std::cerr;
using std::endl;


const TypeEncoding * TypeEncoding::baseClass( int idx ) const
{ 
   return m_pEncoding->getEncoding( baseClasses()[idx] );
}


std::size_t TypeEncoding::getFullInheritanceStaticSize() const
{
   if (isArray())
      return staticSize();
       
   std::size_t nbytes = staticSize(); 
           
   for (uint16_t i = 0; i < numInheritedClasses(); i++ )
      nbytes += baseClass( i )->staticSize();
       
   return nbytes;
}


const TypeEncoding * TypeEncoding::getVariableEncoding( const VarInfo & vi ) const
{
   assert( vi.typeCode >= sg::MAX_BASIC_TYPE );
   return m_pEncoding->getEncoding( vi.typeCode - sg::MAX_BASIC_TYPE );
}


int TypeEncoding::getDerivationFrom( uint16_t type_id ) const
{
   if ( type_id == m_pDataType->getTypeId() )
      return 1;

   const uint16_t * pend  = baseClasses() - 1;
   const uint16_t * p     = baseClasses() + (m_union.numInheritedClasses - 1);
   int        ret   = 2;

   while ( p != pend )
   {
      if ( *p == type_id )
         return ret;
      
      --p;
      ++ret;
   }

   return 0;
}


TypeEncoding::VarInfo  TypeEncoding::getVariable( int nDerivationLevel, int nAttributeNumber ) const
{
   if (isArray())
   {
      VarInfo vi;
      uint16_t aggregate = 1;
           
      vi.byteOffset = m_pEncoding->getStaticVariableSize( m_union.typeCode ) * nAttributeNumber;
      vi.typeCode   = m_union.typeCode;
           
      if ( m_union.typeCode >= sg::MAX_BASIC_TYPE )
         aggregate = m_pEncoding->getEncoding( m_union.typeCode )->numAggregateVars();
           
      vi.linearIndexOffset = aggregate * nAttributeNumber;
           
      return vi;
   }
   else
   {
      const TypeEncoding * p = this;
           
      if (nDerivationLevel < numInheritedClasses())
         p = m_pEncoding->getEncoding( baseClasses()[ nDerivationLevel ] );
           
      return p->varInfo()[ nAttributeNumber ];
   }
}
   
//--------------------------------------------------------------------------------------------------
   
EncodingTable::EncodingTable( int nNumTypes )
{
   m_nCurrentType = 1;
   m_numTypes     = nNumTypes;
   m_ppEncodings  = (TypeEncoding **) m_pool.allocBytes( sizeof(TypeEncoding *) * (nNumTypes + 1) );
}
   
       
EncodingTable::~EncodingTable()
{
}
   
   
uint32_t EncodingTable::getStaticTypeSize( uint16_t typeId ) const
{
   return getStaticSize( typeId + sg::MAX_BASIC_TYPE );
}


uint32_t EncodingTable::getStaticSize( uint16_t typeCode ) const
{
   assert(typeCode != sg::TINSTANCE);
       
   if ( typeCode < sg::TINSTANCE )
      return getBasicTypeSize( (sg::BasicType) typeCode );
              
   return getEncoding( typeCode - sg::MAX_BASIC_TYPE )->getFullInheritanceStaticSize();
}
   
   
const char * EncodingTable::getTypeName( uint16_t typeCode ) const
{
   switch( typeCode )
   {
    case sg::TBOOL        : return "boolean"; 
    case sg::TINT32       : return "int32"; 
    case sg::TUINT32      : return "uint32"; 
    case sg::TINT64       : return "int64"; 
    case sg::TUINT64      : return "uint64"; 
    case sg::TFLOAT       : return "float"; 
    case sg::TDOUBLE      : return "double"; 
    case sg::TBYTE_STRING : return "byte_string";
    case sg::TUUID        : return "uuid"; 
    default:
       const TypeEncoding * p = getEncoding( typeCode - sg::MAX_BASIC_TYPE );
       return p->isArray() ? "array" : p->dataType()->getName();
   }
}

    
void EncodingTable::calcSize( uint16_t typeId )
{
   TypeEncoding * pte = getEncoding( typeId );
           
   if ( pte->staticSize() != 0 )
      return;
       
   uint32_t  nbytes    = 0;
   uint32_t  aggregate = 0;

       
   if ( pte->isArray() )
   {
      int elementSize = 0;
       
      if (pte->arrayIsBasicType())
      {
         elementSize = getBasicTypeSize( (sg::BasicType) pte->arrayType() );
         aggregate   = 1;
      }
      else
      {
         TypeEncoding * t = getEncoding( pte->arrayType() );
         elementSize = t->staticSize();
         aggregate   = t->numAggregateVars();
      }
               
      nbytes    = elementSize * pte->arrayLength();
      aggregate = aggregate   * pte->arrayLength();
   }
   else
   {
      int                     i           = 0;
      uint32_t                baseOffset  = 0;
      uint16_t                baseIndex   = 0;
      uint32_t                byteOffset  = 0;
      uint16_t                indexOffset = 0;
      uint16_t              * pbases      = pte->baseClasses();
      TypeEncoding::VarInfo * vi          = pte->varInfo();
      int                     nvars       = pte->numVars();
      uint32_t                tsize       = 0;
      uint32_t                taggregate  = 0;

      for( i=0; i < pte->numInheritedClasses(); i++ )
      {
         TypeEncoding * p = getEncoding( pbases[i] );
         baseOffset  += p->staticSize();
         baseIndex   += p->numAggregateVars();
      }

      byteOffset  = baseOffset;
      indexOffset = baseIndex;
           
      for( i=0; i < nvars; i++ )
      {
         if( vi[i].typeCode < sg::MAX_BASIC_TYPE )
         {
            taggregate = 1;
            tsize      = getBasicTypeSize( (sg::BasicType) vi[i].typeCode );

            // Align variable
            while( byteOffset % tsize )
               ++byteOffset;                   
         }
         else
         {
            uint16_t      tid = vi[i].typeCode - sg::MAX_BASIC_TYPE;
            TypeEncoding *t   = getEncoding( tid );
                       
            calcSize( tid );

            // Align variable
            while( byteOffset % 8 )
               ++byteOffset;
                   
            tsize      = t->staticSize();
            taggregate = t->numAggregateVars();
         }

         vi[i].byteOffset        = byteOffset; 
         vi[i].linearIndexOffset = indexOffset;

         byteOffset  += tsize;
         indexOffset += taggregate;
      }

      nbytes    = byteOffset - baseOffset;
      aggregate = indexOffset - baseIndex;
   }
       
   if ( aggregate >= 65535 )
      throw EncodingError("Aggregated number of variables exceeds limit (65535)");

   // Pad out the size to an 8-byte alignment
   while( nbytes % 8 )
      ++nbytes;
       
   pte->m_info.static_size = nbytes;
   pte->m_numAggregateVars = (uint16_t) aggregate;       
}

   
void EncodingTable::checkSizes()
{
   // When all types are added, recursively calculate all static sizes
   if (m_nCurrentType == m_numTypes + 1)
   {
      for( uint16_t i=1; i < m_numTypes; i++ )
         calcSize( i );
   }
}
   


TypeEncoding * EncodingTable::addNormalType( DataType *pDataType, const std::vector<VarDefinition> & varDefs, 
                                             uint16_t superclassId, bool isObject, bool isMessage )
{
   int nInstanceCount = 0;
   std::vector<uint16_t> supers;

   if (superclassId)
   {
      TypeEncoding * psuper = getEncoding( superclassId );
      uint16_t     * pid    = psuper->baseClasses();
      uint16_t     * pend   = pid + psuper->numInheritedClasses();
           
      for(; pid != pend; pid++ )
         supers.push_back( *pid );
           
      supers.push_back( superclassId );
   }
       
   TypeEncoding * pte  = (TypeEncoding *)m_pool.allocBytes( sizeof(TypeEncoding) + 
                                                            sizeof(uint16_t) * supers.size() + 
                                                            sizeof(TypeEncoding::VarInfo) * varDefs.size() );
       
   pte->m_info.is_array    = 0;
   pte->m_info.is_object   = isObject  ? 1 : 0;
   pte->m_info.is_message  = isMessage ? 1 : 0;
   pte->m_info.static_size = 0;

   pte->m_pEncoding        = this;
   pte->m_pDataType        = pDataType;
   pte->m_numVars          = varDefs.size();
   pte->m_numAggregateVars = 0;
       
   pte->m_union.numInheritedClasses = supers.size();
       
   uint16_t              * pbase = pte->baseClasses();
   TypeEncoding::VarInfo * pvi   = pte->varInfo();
       
   BOOST_FOREACH( uint16_t base_id, supers )
   {
      *pbase++ = base_id;
   }
              
   BOOST_FOREACH( const VarDefinition & v, varDefs )
   {
      pvi->byteOffset        = 0; // these will be filled in by calcSize
      pvi->linearIndexOffset = 0;
           
      if ( v.basicType == sg::TINSTANCE )
         pvi->typeCode = v.typeId + sg::MAX_BASIC_TYPE;               
      else
         pvi->typeCode = v.basicType;
           
      ++pvi;
   }
       
   m_ppEncodings[ m_nCurrentType++ ] = pte;
       
   checkSizes();
       
   return pte;
}
   
   
//    <4-byte static size> <2-byte type_id | sg::BasicType > <2-byte array length> <1-byte is_basic_type boolean>
void EncodingTable::addArrayType( sg::BasicType basicType, uint16_t typeId, uint16_t arrayLen, bool bIsBasicType )
{
   TypeEncoding *pte = (TypeEncoding *) m_pool.allocBytes( sizeof(TypeEncoding) );
       
   pte->m_info.is_array    = 1;
   pte->m_info.is_object   = 0;
   pte->m_info.is_message  = 0;
   pte->m_info.static_size = 0;

   pte->m_pEncoding        = this;
   pte->m_pDataType        = 0;
   pte->m_numVars          = arrayLen;
   pte->m_numAggregateVars = 0;
       
   pte->m_union.typeCode   = bIsBasicType ? basicType : typeId + sg::MAX_BASIC_TYPE;

   m_ppEncodings[ m_nCurrentType++ ] = pte;

   checkSizes();
}
   
} // end namespace abidos

