#ifndef ABIDOS_COMMON_H
#define ABIDOS_COMMON_H

#include <assert.h>

#include <cstring>
#include <string>
#include <vector>
#include <list>
#include <map>

#include <boost/shared_ptr.hpp>

#include "world_interface.hpp"
#include "abidos_error.hpp"

namespace abidos
{

using namespace std;
    
using boost::int8_t;
using boost::uint8_t;
using boost::int16_t;
using boost::uint16_t;
using boost::int32_t;
using boost::uint32_t;
using boost::int64_t;
using boost::uint64_t;
   
   
   
//--------------------------------------------------------------------------
// CharStarMap
//
// Standard stl::map for use with C-style 'const char *' rather than the
// more common std::string
// 
struct str_less
{
   bool operator()( const char * x, const char * y ) const
   {
      return std::strcmp(x,y) < 0;
   }
};
   
typedef std::map<const char *, const char *, str_less> CharStarMap;

   
typedef boost::shared_ptr<CharStarMap> PCharStarMap;
   

//--------------------------------------------------------------------------
// LocalizedPool
// 
// This pool allocates memory in large blocks then allows users to allocate
// smaller segments from within it. The only advantages this class provides
// over malloc/new is improved locality of reference and not having to worry
// about deallocating memory (all memory allocated by this instance is freed
// by the pool's destructor)
class LocalizedPool
{
   std::list<uint8_t *>        m_pages;
   uint8_t                    *m_pCurrentBlock;
   uint16_t                    m_numAllocated;
   std::size_t                 m_blockSize;
      
   void allocBlock();
      
  public:
      
   LocalizedPool( std::size_t blockSize = 4096 );
   ~LocalizedPool();
      
   // Throws AbidosError if the allocation size exceeds the block size
   uint8_t * allocBytes( int nNumBytes );
};
   
} // end namespace abidos


#endif

