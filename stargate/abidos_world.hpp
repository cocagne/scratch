#ifndef ABIDOS_WORLD_H
#define ABIDOS_WORLD_H

#include <boost/unordered_map.hpp>

#include "abidos_common.hpp"
#include "abidos_uuid.hpp"



namespace abidos
{

class Instance;
       
class DataType;
class EncodingTable;
class TypeEncoding;
class WorldBuilder;
class Instance;
class InstanceControlBlock;
class WorldInterface;
   
typedef boost::intrusive_ptr<InstanceControlBlock> PInstanceControlBlock;

struct Object : public sg::Object
{
   PInstanceControlBlock m_cb;
      
   Object( PInstanceControlBlock cb );

   virtual const sg::UUID * getUUID()     const;
   virtual sg::PInstance    getInstance() const;

   virtual sg::PWorldInterface getOwningInterface() const;

   virtual int getTypeId() const;
   virtual int isType( int nTypeId ) const;

   const UUID * getImplUUID();
       
   void onZeroRefcount();
};
   
struct Message : public sg::Message
{
   PInstanceControlBlock m_cb;
      
   Message( PInstanceControlBlock cb );

   virtual const sg::UUID *getUUID()     const;
   virtual sg::PInstance   getInstance() const;

   const UUID * getImplUUID();
          
   void onZeroRefcount();
};
   
   
class World : public sg::World
{
   typedef std::map<const char *, DataType *, str_less>        DataTypeMap;
   typedef boost::unordered_map< const UUID *, Object *, boost::hash<const UUID*>, puuid_equal > ObjectMap;
   typedef std::list<WorldInterface *> InterfaceList;
   typedef std::vector<DataType *> TypeVec;
      
   LocalizedPool           m_stringPool;
   CharStarMap             m_stringCache;
   TypeVec                 m_dataTypes;
   DataTypeMap             m_typeMap;
   EncodingTable          *m_pEncoding;
   const char             *m_pszName;
   PCharStarMap            m_extraInfo;
   ObjectMap               m_objectMap;
   Instance               *m_pInstanceCache;
   InterfaceList           m_interfaces;
      
   friend class WorldBuilder;
      
  public:
      
   World( const char * pszWorldName, int nNumTypes );
   ~World();

   const char * getName() const;
   
   const PCharStarMap & getExtraInfo() const { return m_extraInfo; }
      
   // Returns a cached copy of the argument. Each unique string is stored only
   // once and all strings are allocated from a common pool with good locality
   // of reference.
   const char * cacheString( const char * psz );
      
     
   Object * createObject( WorldInterface *pwi, uint16_t type_id );


   const TypeVec & types() { return m_dataTypes; }


   sg::PInstance  allocateInstance( PInstanceControlBlock cb, const TypeEncoding * penc, uint8_t *pdat, uint16_t voff );
   void           deallocateInstance( Instance * pi );

   void onZeroRefcount();

   void onZeroRefcount( Object  * obj );
   void onZeroRefcount( Message * msg );


   void addInterface( WorldInterface * pwi );
   void removeInterface( WorldInterface * pwi );
      
   void printTypes();
      
};

   

} // end namespace abidos


#endif

