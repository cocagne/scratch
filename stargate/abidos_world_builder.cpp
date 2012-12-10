#include <stdio.h>
#include <boost/foreach.hpp>


#include "abidos_world_builder.hpp"
#include "abidos_type_encoding.hpp"

namespace abidos
{


sg::WorldBuilder * createWorldBuilder()
{
   return new WorldBuilder();
}




namespace
{
void print_xi( const ExtraInfo & xi )
{
   BOOST_FOREACH( const ExtraInfo::value_type & i, xi )
   {
      fprintf(stderr,"    %s = %s\n", i.first.c_str(), i.second.c_str());
   }
}
      
void perr( const char * msg ) { fprintf(stderr, "%s\n", msg); }
}// end anonymous namespace
      
   
WorldBuilder::WorldBuilder() : m_nextTypeId(1)
{
   fprintf(stderr,"WorldBuilder created!\n");
       
   memset(&m_tinfo, 0, sizeof(m_tinfo));
}
   
   
WorldBuilder::~WorldBuilder()
{
   fprintf(stderr,"WorldBuilder destroyed!\n");
}
   
   
void WorldBuilder::init( const char * name, int num_types, int num_unique_arrays, const ExtraInfo & xi  )
{
   fprintf(stderr,"Initialized world: %s with %d types and %d arrays\n", name, num_types, num_unique_arrays);
   print_xi(xi);
       
   m_nNumTotalTypes = num_types + num_unique_arrays;
   m_pWorld         = new World( name, m_nNumTotalTypes );
       
   world()->m_extraInfo = createMap(xi);
}
   
   
   
PCharStarMap WorldBuilder::createMap( const ExtraInfo & xi )
{
   const char * k;
   const char * v;
   PCharStarMap m( new CharStarMap );
       
   BOOST_FOREACH( const ExtraInfo::value_type & i, xi )
   {
      k = world()->cacheString( i.first.c_str()  );
      v = world()->cacheString( i.second.c_str() );
      (*m)[ k ] = v;
   }
       
   return m;
}

   
void WorldBuilder::addType( const char      * name,
                            sg::TypeType      type_type,
                            int               superclass_id, 
                            int               num_attributes,
                            int               num_types,
                            const ExtraInfo & xi )
{
   if (m_tinfo.pType)
      finishType();
       
   uint16_t typeId = getNextTypeId();
       
   m_tinfo.pType   = new DataType( world(),
                                   world()->cacheString(name), 
                                   createMap(xi), 
                                   typeId, 
                                   superclass_id == -1 ? 0 : world()->m_dataTypes[ superclass_id ] );

   m_tinfo.nAttributes   = num_attributes;
   m_tinfo.nComplexTypes = num_types;
   m_tinfo.bIsObject     = type_type == sg::WB_OBJECT;
   m_tinfo.bIsMessage    = type_type == sg::WB_MESSAGE;
       
   m_tinfo.pType->m_vars.reserve( num_attributes );
       
   //------------------------------------------------------------------------
   // printing
   //
   const char        *otype;
       
   switch ( type_type )
   {
    case sg::WB_TYPE:    otype = "Type";    break;
    case sg::WB_OBJECT:  otype = "Object";  break;
    case sg::WB_MESSAGE: otype = "Message"; break;
    default:
       throw BuildError("Invalid Type Type");
   }
       
   fprintf(stderr,"Adding%s %s Id:%d Parent:%d. Attributes: %d. NTypes %d\n",
           otype, name, typeId, superclass_id, num_attributes, num_types);
   print_xi(xi);
}
   
   
   
void WorldBuilder::addVariable ( const char      * name,
                                 sg::BasicType     btype,
                                 int               type_id, 
                                 const ExtraInfo & xi )
{    
   VarInfo v;
       
   v.pszName      = world()->cacheString( name );
   v.bIsBasicType = btype != sg::TINSTANCE;
   v.extraInfo    = createMap( xi );
       
   if (v.bIsBasicType)
      v.tinfo.basicType = btype;
   else
      v.tinfo.typeId = (uint16_t) type_id;
       
   // TODO: default data
   memset( &v.defaults, 0, sizeof(v.defaults) );
       
   m_tinfo.pType->m_vars.push_back( v );
       
   //------------------------------------------------------------------------
   // printing
   //
   fprintf(stderr,"  AddVar: %s Type %d id:%d\n", name, btype, type_id);       
   print_xi(xi);
}
   
   
   
void WorldBuilder::finishType()
{   
   if (!m_tinfo.pType)
      return; // finalize() always calls this method, skip if unneeded
       
   incrementTypeId();
       
   std::vector<EncodingTable::VarDefinition> varDefs;
       
   BOOST_FOREACH( const VarInfo & vi, m_tinfo.pType->getVars() )
   {
      EncodingTable::VarDefinition vd;
           
      if ( vi.bIsBasicType )
      { 
         vd.basicType = vi.tinfo.basicType;
         vd.typeId    = 0;
      }
      else
      {
         vd.basicType = sg::TINSTANCE;
         vd.typeId    = vi.tinfo.typeId;
      }
           
      varDefs.push_back( vd );
   }

   TypeEncoding *pte = world()->m_pEncoding->addNormalType( m_tinfo.pType,
                                                            varDefs, 
                                                            m_tinfo.pType->getSuperclassId(),
                                                            m_tinfo.bIsObject, 
                                                            m_tinfo.bIsMessage );
       
   world()->m_dataTypes.push_back( m_tinfo.pType );
   world()->m_typeMap[ m_tinfo.pType->getName() ] = m_tinfo.pType;
       
   m_tinfo.pType->m_pEncoding = pte;
       
   m_tinfo.pType = 0;
}

   
void WorldBuilder::addArray( int array_size, sg::BasicType btype, int type_id, bool is_basic_type )
{       
   if (m_tinfo.pType)
      finishType();
       
   world()->m_pEncoding->addArrayType( btype, (uint16_t) type_id, (uint16_t) array_size, is_basic_type );
       
   uint16_t typeId = getNextTypeId();
       
   incrementTypeId();
       
   fprintf(stderr,"Adding array Id: %d,  btype %d,  type_id %d,  isbasic %d\n", typeId, btype, type_id, is_basic_type ? 1 : 0);
}
   
   
   
sg::PWorld WorldBuilder::finalize()
{       
   finishType();
       
   if ( not worldIsComplete() )
      throw BuildError("Mismatch between expected number of types and the number of types defined");
       
   fprintf(stderr, "World Creation Complete\n");
       
   return world();
}
   
} // end namespace abidos

