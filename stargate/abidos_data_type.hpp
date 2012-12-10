#ifndef ABIDOS_DATA_TYPE_H
#define ABIDOS_DATA_TYPE_H

#include <vector>

#include "abidos_common.hpp"

namespace abidos
{

class World;
class WorldBuilder;
class TypeEncoding;
   
struct VarInfo
{
   PCharStarMap extraInfo;
   const char * pszName;
   bool         bIsBasicType;
      
   union {
      sg::BasicType  basicType;
      uint16_t       typeId;
   }tinfo;
      
   union {
      const char * dstring;
      int32_t      dint32;
      uint32_t     duint32;
      int64_t      dint64;
      uint64_t     duint64;
      float        dfloat;
      double       ddouble;
   }defaults;
};

class DataType
{
   World                  *m_pWorld; // Stored here primarily to avoid placing one in each instance
   const char             *m_pszName;
   DataType               *m_pSuperClass;
   TypeEncoding           *m_pEncoding;
   PCharStarMap            m_extraInfo;
   std::vector< VarInfo >  m_vars;
   uint16_t                m_typeId;
   bool                    m_bIsObject;
   bool                    m_bIsMessage;
      
   friend class WorldBuilder;
      
  public:
      
   DataType( World * pWorld, const char * pszName, PCharStarMap extraInfo, uint16_t typeId,  DataType * pSuperClass ) :
         m_pWorld(pWorld), m_pszName( pszName ), m_pSuperClass(pSuperClass), m_extraInfo(extraInfo), m_typeId(typeId)
   {}
      
   void addVar( const VarInfo & v ) { m_vars.push_back(v); }
      
   World *                        getWorld()        const { return m_pWorld;       }
   const char *                   getName()         const { return m_pszName;      }
   const TypeEncoding *           getEncoding()     const { return m_pEncoding;    }
   const PCharStarMap &           getExtraInfo()    const { return m_extraInfo;    }
   const std::vector< VarInfo > & getVars()         const { return m_vars;         }
   std::size_t                    getNumVars()      const { return m_vars.size();  }
   uint16_t                       getTypeId()       const { return m_typeId;       }
   const DataType *               getSuperClass()   const { return m_pSuperClass;  }
   uint16_t                       getSuperclassId() const 
   { 
      return m_pSuperClass ? m_pSuperClass->m_typeId : 0;
   }

   uint16_t getTotalNumVars() const { 
      return m_vars.size() + (m_pSuperClass ? m_pSuperClass->getTotalNumVars() : 0);
   }
      
};
   
} // end namespace abidos


#endif

