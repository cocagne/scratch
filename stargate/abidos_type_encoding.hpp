#ifndef ABIDOS_TYPE_ENCODING_H
#define ABIDOS_TYPE_ENCODING_H

#include <iostream>
#include "abidos_common.hpp"

namespace abidos
{
   
class EncodingError : public AbidosError
{  
  public:
   EncodingError( const std::string & msg ) : AbidosError(msg) {}      
};
   
   
class DataType;
class EncodingTable;

   
// Variable Encoding scheme:
//    Each variable in a DataType has an encoded type byte. This byte is either an element in
//    the sg::BasicType enumeration or an index into the encoding's type array.
// 
//    The encoding's type array contains the full type IDs of the corresponding data structure.
// 
//    If value < sg::MAX_BASIC_TYPE
//          value is a member of sg::BasicType enumeration
//    else
//          value - MAX_BASIC_TYPE = index into the encoding's type array
//
//   The values in the encoding's type array are full EncodingTable type ids.
// 
//   The unorthodox allocation & implementation of this type is done to minimize memory use
//   and increase locality of reference. The encoding/decoding routines using these data
//   structures will be critical to overall performance so we want as many of these to fit
//   within the cache as possible.
//
// 
struct TypeEncoding
{
   struct BitSet
   {
      unsigned int is_array:1;
      unsigned int is_object:1;
      unsigned int is_message:1;
      unsigned int static_size:29;
   } m_info;

   EncodingTable *m_pEncoding;
   DataType      *m_pDataType;
   uint16_t       m_numAggregateVars; // number of variables recursively contained within the structure
   uint16_t       m_numVars;          // number of variables in just this type
      
   union 
   {
      uint16_t numInheritedClasses;               
      uint16_t typeCode;
   }m_union;

      
      
   //---------------------------------------------------
   // Non Array Interface 
   // 
   struct VarInfo {
      uint32_t byteOffset;       // Offset in bytes from start of root baseclass
      uint16_t linearIndexOffset;// Linear variable number. 
      uint16_t typeCode;         // BasicType if < sg::MAX_BASIC_TYPE, type_id - MAX_BA... otherwise
   };
      
   uint16_t * baseClasses()             { return (uint16_t *) &this[1]; }
   const uint16_t * baseClasses() const { return (uint16_t *) &this[1]; }
      
   const TypeEncoding * baseClass( int idx ) const;
      
   VarInfo *  varInfo()                 { return (VarInfo *) (baseClasses() + m_union.numInheritedClasses); }
   const VarInfo *  varInfo() const     { return (const VarInfo *) (baseClasses() + m_union.numInheritedClasses); }
      
   uint16_t numInheritedClasses() const { return m_union.numInheritedClasses; }
      
   uint16_t superclassId() const
   {
      if (m_union.numInheritedClasses == 0)
         return 0;
      else
         return *( baseClasses() + (m_union.numInheritedClasses - 1) );
   }
      
   const TypeEncoding * getVariableEncoding( const VarInfo & vi ) const;
      
   std::size_t getFullInheritanceStaticSize() const;

   // 0 for not derived from type_id
   // 1 for is exact instance of type_id
   // X + 1 for X number of classes between this type and type_id
   int getDerivationFrom( uint16_t type_id ) const;
      
      
   //---------------------------------------------------
   // Array Interface
   //
   uint16_t arrayLength()      const { return m_numVars;                        }
   bool     arrayIsBasicType() const { return m_union.typeCode < sg::TINSTANCE; }
   uint16_t arrayType()        const
   { 
      return arrayIsBasicType() ? m_union.typeCode : m_union.typeCode - sg::MAX_BASIC_TYPE; 
   }
      
      
   //---------------------------------------------------
   // Shared Interface
   // 
   std::size_t staticSize() const { return m_info.static_size; }
      
   bool        isArray()    const { return m_info.is_array;   }
   bool        isObject()   const { return m_info.is_object;  }
   bool        isMessage()  const { return m_info.is_message; }

   DataType *  dataType()         const { return m_pDataType;        }
   uint16_t    numVars()          const { return m_numVars;          }
   uint16_t    numAggregateVars() const { return m_numAggregateVars; }
      
   const EncodingTable * encodingTable() const { return m_pEncoding; }
      
   VarInfo     getVariable( int nDerivationLevel, int nAttributeNumber ) const;
      
   VarInfo     getVariable( const sg::AttributeID & aid ) const
   {
      return getVariable( aid.nDerivationLevel, aid.nAttributeNumber );
   }
      
      
  private:
      
   // Completely disallow all construction, destruction, & copying. 
   TypeEncoding();
   ~TypeEncoding();
   TypeEncoding( const TypeEncoding & );
   void operator=( const TypeEncoding & );
      
   friend class EncodingTable;
};
   
   
inline std::size_t getBasicTypeSize( sg::BasicType bt )
{
   switch( bt )
   {
    case sg::TBOOL        : return 1; 
    case sg::TINT32       : return 4; 
    case sg::TUINT32      : return 4; 
    case sg::TINT64       : return 8; 
    case sg::TUINT64      : return 8; 
    case sg::TFLOAT       : return 4; 
    case sg::TDOUBLE      : return 8; 
    case sg::TBYTE_STRING : return sizeof(void*); 
    case sg::TUUID        : return sizeof(void*);
    default:
       assert(0);
   }
}
   
    
   
class EncodingTable
{
   LocalizedPool               m_pool;
   TypeEncoding              **m_ppEncodings;
   int                         m_nCurrentType;
   uint16_t                    m_numTypes;
            
   void calcSize( uint16_t typeId );
      
   void checkSizes();
      
   uint32_t getStaticSize( uint16_t typeCode ) const;
      
  public:
      
   EncodingTable( int nNumTypes );
   ~EncodingTable();
      
   struct VarDefinition
   {
      sg::BasicType  basicType;
      uint16_t       typeId;
   };

   // Throws EncodingError if the encoding exceeds sane sizes
   TypeEncoding * addNormalType( DataType *pDataType, const std::vector<VarDefinition> & varDefs, uint16_t superclassId, bool isObject, bool isMessage );
      
   void addArrayType( sg::BasicType basicType, uint16_t typeId, uint16_t arrayLen, bool bIsBasicType );
      
   // TypeID 0 is reserved for "invalid type". Thus it will reutrn a null pointer.
   TypeEncoding * getEncoding( uint16_t typeId ) { assert(typeId <= m_numTypes); return m_ppEncodings[typeId]; }
   const TypeEncoding * getEncoding( uint16_t typeId ) const { assert(typeId <= m_numTypes); return m_ppEncodings[typeId]; }
      
   int            getNumEncodings() const { return m_numTypes; }
      
   uint32_t getStaticTypeSize( uint16_t typeId ) const;
   uint32_t getStaticVariableSize( uint16_t typeCode ) const { return getStaticSize( typeCode ); }
      
   const char * getTypeName( uint16_t typeCode ) const;
};
   
   
} // end namespace abidos


#endif

